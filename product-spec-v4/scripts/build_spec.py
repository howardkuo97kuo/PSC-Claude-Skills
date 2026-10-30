#!/usr/bin/env python3
"""Build a Product Specification .docx from a JSON content file and the master template.

Usage:
    python3 build_spec.py <content.json> <out.docx> [--master assets/master.docx] [--no-paginate]

All formatting (fonts, heading styles, table colours, header/footer, cover, sign-off table,
page setup) comes from the master docx. This script only replaces content:
  * cover fields and Record of Revision rows
  * the table of contents (regenerated: hyperlinks + bookmarks + page numbers)
  * the whole body (rebuilt from the JSON blocks)

Page numbers: the document is built, converted to PDF with LibreOffice, every heading is
located on its page, then the TOC and cover "Total Pages" are filled in and the document
is rebuilt until the numbers are stable.

See references/content_schema.md for the JSON format.
"""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MASTER = os.path.join(HERE, '..', 'assets', 'master.docx')

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

# ---- formatting constants copied from the master -------------------------------------
BORDER = '<w:{s} w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
TBL_BORDERS = ''.join(BORDER.format(s=s) for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
CELL_BORDERS = ''.join(BORDER.format(s=s) for s in ('top', 'left', 'bottom', 'right'))
CELL_MAR = ('<w:tcMar><w:top w:w="20" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
            '<w:bottom w:w="20" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tcMar>')
HEADER_FILL = '2D6A4F'
BAND_FILL = 'EEF3F8'
GROUP_FILL = 'EAF1F8'
ACCENT = '1F4E79'
RPR = '<w:rFonts w:eastAsia="Calibri"/>'
PORTRAIT_WIDTH_DXA = 10106          # usable table width in the portrait section
LANDSCAPE_WIDTH_DXA = 15038
PORTRAIT_MAX_CM = (17.5, 22.0)       # max image width/height
LANDSCAPE_MAX_CM = (26.0, 13.5)
EMU_PER_CM = 360000
KEEP_TABLE_MAX_ROWS = 12            # tables up to this many rows are kept on one page


def t(text):
    return f'<w:t xml:space="preserve">{escape(str(text))}</w:t>'


def run(text, rpr=RPR):
    """A run; '\n' inside text becomes a line break."""
    parts = str(text).split('\n')
    inner = '<w:br/>'.join(t(p) for p in parts)
    return f'<w:r><w:rPr>{rpr}</w:rPr>{inner}</w:r>'


def text_of(el):
    return ''.join(n.text or '' for n in el.iter(qn('w:t')))


def P(xml):
    return parse_xml(f'<w:p {NS}>{xml}</w:p>')


def slug(num, text):
    s = re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_')
    return ('sec_' + num.replace('.', '_').strip('_') + '_' + s)[:40]


class Builder:
    def __init__(self, master, content, pages=None):
        self.doc = Document(master)
        self.c = content
        self.pages = pages or {}
        self.body = self.doc.element.body
        self.fig = 0
        self.tab = 0
        self.bm_id = 500
        self.headings = []          # (level, number, text, bookmark)
        self.counters = [0, 0, 0]
        self.orient = 'portrait'
        self.first_in_section = True
        self._locate_master_parts()

    # ---- master structure ------------------------------------------------------------
    def _locate_master_parts(self):
        kids = list(self.body)
        self.contents_p = None
        for i, el in enumerate(kids):
            txt = text_of(el).strip()
            if el.tag == qn('w:p') and txt == 'Contents' and self.contents_p is None:
                self.contents_p = el
                ci = i
        if self.contents_p is None:
            sys.exit('Master has no "Contents" paragraph')
        # TOC lines: paragraphs after Contents until the paragraph holding a sectPr
        self.toc_old = []
        j = ci + 1
        while kids[j].find('.//' + qn('w:sectPr')) is None:
            self.toc_old.append(kids[j])
            j += 1
        self.toc_sect_p = kids[j]
        body_start = j + 1
        self.final_sect = kids[-1]
        assert self.final_sect.tag == qn('w:sectPr')
        # section-property prototypes from the body sections of the master
        self.sect_proto = {}
        for el in kids[body_start:]:
            sp = el if el.tag == qn('w:sectPr') else el.find('.//' + qn('w:sectPr'))
            if sp is None:
                continue
            pg = sp.find(qn('w:pgSz'))
            o = 'landscape' if pg.get(qn('w:orient')) == 'landscape' else 'portrait'
            self.sect_proto.setdefault(o, copy.deepcopy(sp))
        for el in self.toc_old + kids[body_start:-1]:
            self.body.remove(el)
        self.cover_tbl = self.body.findall(qn('w:tbl'))[0]
        self.sign_tbl = self.body.findall(qn('w:tbl'))[1]
        self.rev_tbl = self.body.findall(qn('w:tbl'))[2]

    # ---- cover / revision --------------------------------------------------------------
    @staticmethod
    def _set_cell_text(tc, text):
        """Replace a cell's text, keeping the first paragraph's formatting.
        Each '\n'-separated line becomes its own paragraph (as in the master cover)."""
        ps = tc.findall(qn('w:p'))
        proto = copy.deepcopy(ps[0])
        runs = proto.findall(qn('w:r'))
        rpr = runs[0].find(qn('w:rPr')) if runs else None
        rpr_xml = re.sub(r'^<w:rPr[^>]*>|</w:rPr>$', '', rpr.xml) if rpr is not None else RPR
        for p in ps:
            tc.remove(p)
        lines = str(text).split('\n') if text not in (None, '') else ['']
        for line in lines:
            p = copy.deepcopy(proto)
            for ch in list(p):
                if ch.tag != qn('w:pPr'):
                    p.remove(ch)
            if line:
                for r in P(run(line, rpr_xml)).findall(qn('w:r')):
                    p.append(r)
            tc.append(p)

    def fill_cover(self):
        cov = self.c['cover']
        labels = {'Project Name': 'project_name', 'Model No.': 'model_no', 'Description': 'description',
                  'Document No.': 'document_no', 'Version': 'version', 'Total Pages': 'total_pages',
                  'Date': 'date'}
        for tr in self.cover_tbl.findall(qn('w:tr')):
            tcs = tr.findall(qn('w:tc'))
            if len(tcs) < 2:
                continue
            label = text_of(tcs[0]).strip().rstrip(':').strip()
            key = labels.get(label)
            if key is None:
                continue
            val = self.pages.get('_total') if key == 'total_pages' else cov.get(key, '')
            self._set_cell_text(tcs[1], '' if val is None else val)
        self.fill_signoff(cov)
        rows = self.rev_tbl.findall(qn('w:tr'))[1:]
        revs = self.c.get('revisions', [])
        if len(revs) > len(rows):
            sys.exit(f'Record of Revision has {len(rows)} rows in the master; got {len(revs)} revisions')
        for tr, rev in zip(rows, revs):
            for tc, val in zip(tr.findall(qn('w:tc')), rev):
                self._set_cell_text(tc, val)

    def fill_signoff(self, cov):
        """Approved / Checked / Prepared By: names from the cover. Signature cells are always
        left empty - the people sign the printed document by hand."""
        rows = self.sign_tbl.findall(qn('w:tr'))
        for key, sig_tc, name_tc in zip(('approved_by', 'checked_by', 'prepared_by'),
                                        rows[1].findall(qn('w:tc')), rows[2].findall(qn('w:tc'))):
            self._set_cell_text(name_tc, cov.get(key, '') or '')
            p = sig_tc.find(qn('w:p'))
            for r in p.findall(qn('w:r')):
                p.remove(r)

    # ---- body helpers ------------------------------------------------------------------
    def add(self, el):
        self.final_sect.addprevious(el)

    def heading(self, level, text):
        self.counters[level - 1] += 1
        for k in range(level, 3):
            self.counters[k] = 0
        num = '.'.join(str(n) for n in self.counters[:level])
        label = f'{num}. {text}' if level == 1 else f'{num} {text}'
        bm = slug(num, text)
        self.bm_id += 1
        self.headings.append((level, label, bm))
        if level == 1:
            pb = '' if self.first_in_section else '<w:pageBreakBefore/>'
            ppr = f'<w:pStyle w:val="Heading1"/>{pb}<w:spacing w:after="160"/>'
        else:
            ppr = (f'<w:pStyle w:val="Heading{level}"/><w:keepNext/>'
                   '<w:spacing w:before="240" w:after="120"/>')
        self.add(P(f'<w:pPr>{ppr}</w:pPr><w:bookmarkStart w:id="{self.bm_id}" w:name="{bm}"/>'
                   f'<w:r>{t(label)}</w:r><w:bookmarkEnd w:id="{self.bm_id}"/>'))
        self.first_in_section = False

    def para(self, text, kind='body'):
        if kind == 'note':
            rpr = RPR + '<w:i/><w:color w:val="595959"/>'
            ppr = '<w:spacing w:before="240" w:after="120" w:line="259" w:lineRule="auto"/>'
        elif kind == 'connector':
            rpr = RPR + f'<w:b/><w:bCs/><w:color w:val="{ACCENT}"/>'
            ppr = (f'<w:keepNext/><w:pBdr><w:left w:val="single" w:sz="24" w:space="6" w:color="{ACCENT}"/>'
                   f'</w:pBdr><w:shd w:val="clear" w:color="auto" w:fill="{GROUP_FILL}"/>'
                   '<w:spacing w:before="240" w:after="120"/>')
        elif kind == 'lead':        # a body line that introduces the next element
            rpr = RPR
            ppr = '<w:keepNext/><w:spacing w:after="120" w:line="259" w:lineRule="auto"/>'
        else:
            rpr = RPR
            ppr = '<w:spacing w:after="120" w:line="259" w:lineRule="auto"/>'
        self.add(P(f'<w:pPr>{ppr}</w:pPr>{run(text, rpr)}'))
        self.first_in_section = False

    def bullets(self, items):
        for it in items:
            self.add(P('<w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/>'
                       '<w:numId w:val="2"/></w:numPr><w:spacing w:after="60"/></w:pPr>' + run(it)))
        self.first_in_section = False

    def caption(self, kind, text):
        if kind == 'figure':
            self.fig += 1
            label = f'Figure {self.fig} – {text}'
            ppr = '<w:spacing w:before="40" w:after="200"/><w:jc w:val="center"/>'
        else:
            self.tab += 1
            label = f'Table {self.tab} – {text}'
            ppr = '<w:keepNext/><w:spacing w:before="200" w:after="80"/><w:jc w:val="center"/>'
        self.add(P(f'<w:pPr>{ppr}</w:pPr>' + run(label, RPR + '<w:i/><w:iCs/><w:sz w:val="18"/><w:szCs w:val="18"/>')))

    def _inline(self, path, width_cm=None, height_cm=None):
        if not os.path.exists(path):
            sys.exit(f'Image not found: {path}')
        with Image.open(path) as im:
            pw, ph = im.size
        maxw, maxh = PORTRAIT_MAX_CM if self.orient == 'portrait' else LANDSCAPE_MAX_CM
        if width_cm and height_cm:
            w, h = width_cm, height_cm
        elif height_cm:
            h = height_cm
            w = h * pw / ph
        else:
            w = width_cm or maxw
            h = w * ph / pw
        scale = min(1.0, maxw / w, maxh / h)
        w, h = w * scale, h * scale
        inline = self.doc.part.new_pic_inline(path, int(w * EMU_PER_CM), int(h * EMU_PER_CM))
        r = parse_xml(f'<w:r {NS}><w:rPr><w:noProof/></w:rPr><w:drawing/></w:r>')
        r.find(qn('w:drawing')).append(inline)
        return r

    def image(self, path, caption=None, width_cm=None, height_cm=None):
        p = P('<w:pPr><w:keepNext/><w:spacing w:before="120"/><w:jc w:val="center"/></w:pPr>')
        p.append(self._inline(path, width_cm, height_cm))
        self.add(p)
        if caption:
            self.caption('figure', caption)
        self.first_in_section = False

    # ---- tables ------------------------------------------------------------------------
    def _cell(self, w, content, align='L', fill=None, bold=False, color=None, vmerge=None,
              header=False, keep=True):
        tcpr = f'<w:tcW w:w="{w}" w:type="dxa"/>'
        if vmerge:
            tcpr += f'<w:vMerge w:val="restart"/>' if vmerge == 'restart' else '<w:vMerge/>'
        tcpr += f'<w:tcBorders>{CELL_BORDERS}</w:tcBorders>'
        if fill:
            tcpr += f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
        tcpr += CELL_MAR + '<w:vAlign w:val="center"/>'
        jc = '<w:jc w:val="center"/>' if align == 'C' else ''
        rpr = RPR
        if header:
            rpr += '<w:b/><w:bCs/><w:color w:val="FFFFFF"/>'
        elif bold:
            rpr += f'<w:b/><w:color w:val="{color or ACCENT}"/>'
        img = None
        if isinstance(content, dict):
            img = content.get('image')
            text = content.get('text', '')
            img_h = content.get('image_height_cm', 1.3)
        else:
            text = '' if content is None else str(content)
        tc = parse_xml(f'<w:tc {NS}><w:tcPr>{tcpr}</w:tcPr></w:tc>')
        if img:
            ip = P('<w:pPr><w:spacing w:before="20"/><w:jc w:val="center"/></w:pPr>')
            ip.append(self._inline(img, height_cm=img_h))
            tc.append(ip)
        lines = text.split('\n') if text != '' else ['']
        for line in lines:
            body = run(line, rpr) if line != '' else ''
            kn = '<w:keepNext/>' if keep else ''
            tc.append(P(f'<w:pPr>{kn}{jc}</w:pPr>{body}'))
        return tc

    def table(self, spec, caption=None):
        if caption:
            self.caption('table', caption)
        header = spec['header']
        rows = spec['rows']
        n = len(header)
        total = PORTRAIT_WIDTH_DXA if self.orient == 'portrait' else LANDSCAPE_WIDTH_DXA
        widths = spec.get('widths')
        if widths:
            s = sum(widths)
            widths = [round(w * total / s) for w in widths]
            widths[-1] += total - sum(widths)
        else:
            widths = [total // n] * n
            widths[-1] += total - sum(widths)
        align = spec.get('align') or (['L'] * n)
        group = spec.get('group_first_col', False)
        band = spec.get('band', not group)
        row_h = spec.get('row_height')
        grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        tbl = parse_xml(
            f'<w:tbl {NS}><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/>'
            f'<w:tblBorders>{TBL_BORDERS}</w:tblBorders><w:tblCellMar><w:left w:w="10" w:type="dxa"/>'
            '<w:right w:w="10" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="04A0" w:firstRow="1" '
            'w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid></w:tbl>')
        tr = parse_xml(f'<w:tr {NS}><w:trPr><w:cantSplit/><w:tblHeader/><w:jc w:val="center"/></w:trPr></w:tr>')
        for w, h in zip(widths, header):
            tr.append(self._cell(w, h, 'C', HEADER_FILL, header=True))
        tbl.append(tr)
        for ri, row in enumerate(rows):
            if len(row) != n:
                sys.exit(f'Row has {len(row)} cells, header has {n}: {row}')
            trh = f'<w:trHeight w:val="{row_h}"/>' if row_h else ''
            tr = parse_xml(f'<w:tr {NS}><w:trPr><w:cantSplit/>{trh}<w:jc w:val="center"/></w:trPr></w:tr>')
            fill = BAND_FILL if band and ri % 2 == 1 else None
            keep = len(rows) <= KEEP_TABLE_MAX_ROWS and ri < len(rows) - 1
            for ci, (w, val) in enumerate(zip(widths, row)):
                if group and ci == 0:
                    nxt = rows[ri + 1][0] if ri + 1 < len(rows) else 'x'
                    if val in ('', None):
                        vm = 'continue'
                    elif nxt in ('', None):
                        vm = 'restart'
                    else:
                        vm = None
                    tr.append(self._cell(w, val, 'L', GROUP_FILL, bold=val not in ('', None), vmerge=vm,
                                         keep=keep))
                else:
                    tr.append(self._cell(w, val, align[ci], fill, keep=keep))
            tbl.append(tr)
        self.add(tbl)
        self.first_in_section = False

    def connector(self, blk):
        title = f"{blk['ref']} : {blk['function']} - {blk['part']}"
        self.para(title, 'connector')
        if blk.get('image'):
            p = P('<w:pPr><w:keepNext/><w:spacing w:before="120"/><w:jc w:val="center"/></w:pPr>')
            p.append(self._inline(blk['image'], height_cm=blk.get('image_height_cm', 2.5)))
            self.add(p)
        self.table({'header': ['Pin No.', 'Pin Name', 'Description'], 'widths': [1400, 2700, 6006],
                    'align': ['C', 'L', 'L'], 'rows': blk['pins']}, f'{title} Pin Assignment')
        if blk.get('note'):
            self.para(blk['note'], 'note')

    def section(self, orient):
        if orient == self.orient:
            return
        sp = copy.deepcopy(self.sect_proto[self.orient])
        p = P('<w:pPr/>')
        p.find(qn('w:pPr')).append(sp)
        self.add(p)
        self.orient = orient
        self.first_in_section = True

    # ---- TOC ---------------------------------------------------------------------------
    def toc(self):
        anchor = self.contents_p
        for level, label, bm in self.headings:
            page = self.pages.get(bm, 0)
            ind = {1: '', 2: '<w:ind w:left="260"/>', 3: '<w:ind w:left="520"/>'}[level]
            rpr = RPR + ('<w:b/><w:bCs/>' if level == 1 else '') + '<w:sz w:val="24"/><w:szCs w:val="24"/>'
            p = P('<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8806"/></w:tabs>'
                  f'<w:spacing w:after="80"/>{ind}</w:pPr>'
                  f'<w:hyperlink w:anchor="{bm}" w:history="1">'
                  f'<w:r><w:rPr>{rpr}</w:rPr>{t(label)}</w:r>'
                  f'<w:r><w:rPr>{rpr}</w:rPr><w:tab/>{t(page)}</w:r></w:hyperlink>')
            anchor.addnext(p)
            anchor = p

    # ---- final -------------------------------------------------------------------------
    def drop_orphan_images(self):
        xml = self.doc.element.xml
        for rid, rel in list(self.doc.part.rels.items()):
            if 'image' in rel.reltype and f'"{rid}"' not in xml:
                self.doc.part.drop_rel(rid)

    def build(self, out):
        self.fill_cover()
        for blk in self.c['body']:
            k = blk['type']
            if k in ('h1', 'h2', 'h3'):
                self.heading(int(k[1]), blk['text'])
            elif k == 'p':
                self.para(blk['text'], blk.get('style', 'body'))
            elif k == 'note':
                self.para(blk['text'], 'note')
            elif k == 'bullets':
                self.bullets(blk['items'])
            elif k == 'image':
                self.image(blk['path'], blk.get('caption'), blk.get('width_cm'), blk.get('height_cm'))
            elif k == 'table':
                self.table(blk, blk.get('caption'))
            elif k == 'connector':
                self.connector(blk)
            elif k == 'section':
                self.section(blk['orient'])
            else:
                sys.exit(f'Unknown block type: {k}')
        # final section orientation
        final = copy.deepcopy(self.sect_proto[self.orient])
        self.final_sect.addprevious(final)
        self.body.remove(self.final_sect)
        self.final_sect = final
        self.toc()
        self.drop_orphan_images()
        self.doc.save(out)
        return self.headings


# ---- pagination ---------------------------------------------------------------------
def pdf_pages(docx_path, work):
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', work, docx_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(work, os.path.splitext(os.path.basename(docx_path))[0] + '.pdf')
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], check=True, capture_output=True,
                         text=True).stdout
    return pdf, txt.split('\f')[:-1] if txt.endswith('\f') else txt.split('\f')


def norm(s):
    return re.sub(r'\s+', ' ', s.replace('&', '&')).strip()


def locate(headings, pages):
    """Map bookmark -> 1-based page by finding each heading line after the Contents page."""
    start = 0
    for i, pg in enumerate(pages):
        if re.search(r'^\s*Contents\s*$', pg, re.M):
            start = i + 1
    # skip remaining TOC pages (lines ending in dotted leaders)
    while start < len(pages) and re.search(r'\.{6,}\s*\d+\s*$', pages[start], re.M):
        start += 1
    result, cur = {}, start
    for level, label, bm in headings:
        key = norm(label)[:45]
        found = None
        for i in range(cur, len(pages)):
            lines = [norm(l) for l in pages[i].splitlines()]
            if any(l.startswith(key) for l in lines):
                found = i
                break
        if found is None:
            result[bm] = 0
        else:
            result[bm] = found + 1
            cur = found
    result['_total'] = len(pages)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('content')
    ap.add_argument('out')
    ap.add_argument('--master', default=DEFAULT_MASTER)
    ap.add_argument('--no-paginate', action='store_true')
    a = ap.parse_args()
    content = json.load(open(a.content, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(a.content))
    for blk in content['body']:                      # resolve relative image paths
        for key in ('path', 'image'):
            if isinstance(blk.get(key), str) and not os.path.isabs(blk[key]):
                blk[key] = os.path.join(base, blk[key])
        if blk.get('type') == 'table':
            for row in blk['rows']:
                for cell in row:
                    if isinstance(cell, dict) and cell.get('image') and not os.path.isabs(cell['image']):
                        cell['image'] = os.path.join(base, cell['image'])
    pages = {}
    headings = Builder(a.master, content, pages).build(a.out)
    if a.no_paginate:
        return
    work = tempfile.mkdtemp()
    for attempt in range(4):
        _, ptxt = pdf_pages(a.out, work)
        new = locate(headings, ptxt)
        if new == pages:
            break
        pages = new
        headings = Builder(a.master, content, pages).build(a.out)
    missing = [bm for _, _, bm in headings if pages.get(bm, 0) == 0]
    print(f'built {a.out}: {pages.get("_total")} pages, {len(headings)} headings'
          + (f', NOT FOUND on any page: {missing}' if missing else ''))
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
