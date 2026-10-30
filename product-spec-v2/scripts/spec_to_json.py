#!/usr/bin/env python3
"""Convert an existing Product Specification .docx (built on the master) back to content JSON.

Usage:
    python3 spec_to_json.py <product_spec.docx> <out_dir>

Writes <out_dir>/content.json and <out_dir>/media/*.  Use it to:
  * start a new revision of a Product Spec from the previous release, or
  * regression-test build_spec.py (build the JSON again and compare).
"""
import json
import os
import re
import sys

from docx import Document
from docx.oxml.ns import qn

CAP_RE = re.compile(r'^(Figure|Table)\s+\d+\s+[–-]\s+(.*)$')
HEAD_RE = re.compile(r'^\d+(\.\d+)*\.?\s+')


def text_of(el):
    out = []
    for node in el.iter():
        if node.tag == qn('w:t'):
            out.append(node.text or '')
        elif node.tag == qn('w:br'):
            out.append('\n')
        elif node.tag == qn('w:tab'):
            out.append('\t')
    return ''.join(out)


class Conv:
    def __init__(self, path, out):
        self.doc = Document(path)
        self.out = out
        self.media = os.path.join(out, 'media')
        os.makedirs(self.media, exist_ok=True)
        self.n_img = 0

    def save_images(self, el):
        paths = []
        for blip in el.iter(qn('a:blip')):
            rid = blip.get(qn('r:embed'))
            part = self.doc.part.related_parts[rid]
            ext = os.path.splitext(part.partname)[1]
            self.n_img += 1
            name = f'img{self.n_img:02d}{ext}'
            with open(os.path.join(self.media, name), 'wb') as f:
                f.write(part.blob)
            ext_el = el.find('.//' + qn('wp:extent'))
            h_cm = int(ext_el.get('cy')) / 360000 if ext_el is not None else None
            w_cm = int(ext_el.get('cx')) / 360000 if ext_el is not None else None
            paths.append((f'media/{name}', round(w_cm, 2), round(h_cm, 2)))
        return paths

    def table(self, tbl):
        grid = [int(g.get(qn('w:w'))) for g in tbl.find(qn('w:tblGrid')).findall(qn('w:gridCol'))]
        trs = tbl.findall(qn('w:tr'))
        header = [text_of(tc).strip() for tc in trs[0].findall(qn('w:tc'))]
        rows, group, band = [], False, False
        align = None
        for ri, tr in enumerate(trs[1:]):
            row = []
            tcs = tr.findall(qn('w:tc'))
            if align is None:
                align = ['C' if tc.find('.//' + qn('w:jc')) is not None and
                         tc.find('.//' + qn('w:jc')).get(qn('w:val')) == 'center' else 'L' for tc in tcs]
            for ci, tc in enumerate(tcs):
                shd = tc.find('.//' + qn('w:shd'))
                fill = shd.get(qn('w:fill')) if shd is not None else None
                if ci == 0 and fill == 'EAF1F8':
                    group = True
                if fill == 'EEF3F8':
                    band = True
                vm = tc.find('.//' + qn('w:vMerge'))
                txt = '\n'.join(text_of(p).strip() for p in tc.findall(qn('w:p')) if text_of(p).strip())
                if vm is not None and vm.get(qn('w:val')) != 'restart':
                    txt = ''
                imgs = self.save_images(tc)
                if imgs:
                    row.append({'image': imgs[0][0], 'image_height_cm': imgs[0][2], 'text': txt})
                else:
                    row.append(txt)
            rows.append(row)
        trh = trs[1].find('.//' + qn('w:trHeight')) if len(trs) > 1 else None
        spec = {'type': 'table', 'header': header, 'rows': rows, 'widths': grid, 'align': align}
        if group:
            spec['group_first_col'] = True
        if not band and not group:
            spec['band'] = False
        if trh is not None:
            spec['row_height'] = int(trh.get(qn('w:val')))
        return spec

    def run(self):
        body = self.doc.element.body
        kids = list(body)
        tbls = body.findall(qn('w:tbl'))
        cover = {}
        keys = {'Project Name': 'project_name', 'Model No.': 'model_no', 'Description': 'description',
                'Document No.': 'document_no', 'Version': 'version', 'Total Pages': 'total_pages',
                'Date': 'date'}
        for tr in tbls[0].findall(qn('w:tr')):
            tcs = tr.findall(qn('w:tc'))
            if len(tcs) >= 2:
                k = keys.get(text_of(tcs[0]).strip().rstrip(':').strip())
                if k:
                    cover[k] = '\n'.join(text_of(p).strip() for p in tcs[1].findall(qn('w:p'))
                                         if text_of(p).strip())
        cover.pop('total_pages', None)
        srows = tbls[1].findall(qn('w:tr'))
        for key, tc in zip(('approved_by', 'checked_by', 'prepared_by'), srows[2].findall(qn('w:tc'))):
            cover[key] = text_of(tc).strip()
        revisions = []
        for tr in tbls[2].findall(qn('w:tr'))[1:]:
            vals = [text_of(tc).strip() for tc in tr.findall(qn('w:tc'))]
            if any(vals):
                revisions.append(vals)
        # body starts after the paragraph holding the TOC section break
        start = None
        seen_contents = False
        for i, el in enumerate(kids):
            if el.tag == qn('w:p') and text_of(el).strip() == 'Contents':
                seen_contents = True
            if seen_contents and el.find('.//' + qn('w:sectPr')) is not None:
                start = i + 1
                break
        blocks = []
        pending_caption = None
        orient = 'portrait'
        conn = None
        for el in kids[start:]:
            if el.tag == qn('w:sectPr'):
                break
            if el.tag == qn('w:tbl'):
                spec = self.table(el)
                if pending_caption:
                    spec['caption'] = pending_caption
                    pending_caption = None
                if conn is not None and spec['header'][:1] == ['Pin No.'] and 'pins' not in conn:
                    conn['pins'] = spec['rows']
                    continue
                conn = None
                blocks.append(spec)
                continue
            sp = el.find('.//' + qn('w:sectPr'))
            ppr = el.find(qn('w:pPr'))
            style = ppr.find(qn('w:pStyle')).get(qn('w:val')) if ppr is not None and ppr.find(qn('w:pStyle')) is not None else ''
            txt = text_of(el).strip()
            imgs = self.save_images(el)
            if style.startswith('Heading'):
                conn = None
                lvl = int(style[-1])
                blocks.append({'type': f'h{lvl}', 'text': HEAD_RE.sub('', txt)})
            elif style == 'ListParagraph':
                if blocks and blocks[-1]['type'] == 'bullets':
                    blocks[-1]['items'].append(txt)
                else:
                    blocks.append({'type': 'bullets', 'items': [txt]})
            elif imgs:
                if conn is not None and 'image' not in conn and 'pins' not in conn:
                    conn['image'] = imgs[0][0]
                    conn['image_height_cm'] = imgs[0][2]
                else:
                    blocks.append({'type': 'image', 'path': imgs[0][0], 'width_cm': imgs[0][1]})
            elif CAP_RE.match(txt):
                kind, cap = CAP_RE.match(txt).groups()
                if kind == 'Figure':
                    for b in reversed(blocks):
                        if b['type'] == 'image':
                            b['caption'] = cap
                            break
                elif conn is None:
                    pending_caption = cap
            elif ppr is not None and ppr.find(qn('w:pBdr')) is not None:
                m = re.match(r'^(.*?)\s:\s(.*?)\s-\s(.*)$', txt)
                conn = {'type': 'connector', 'ref': m.group(1), 'function': m.group(2), 'part': m.group(3)}
                blocks.append(conn)
            elif txt:
                is_note = 'w:color w:val="595959"' in el.xml
                if is_note and conn is not None:
                    conn['note'] = txt
                elif is_note:
                    blocks.append({'type': 'note', 'text': txt})
                else:
                    conn = None
                    blocks.append({'type': 'p', 'text': txt})
            if sp is not None:
                # the section that ENDS here has this sectPr; the next one is the other orientation
                nxt = 'landscape' if orient == 'portrait' else 'portrait'
                blocks.append({'type': 'section', 'orient': nxt})
                orient = nxt
        data = {'cover': cover, 'revisions': revisions, 'body': blocks}
        with open(os.path.join(self.out, 'content.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f'{len(blocks)} blocks, {self.n_img} images -> {self.out}/content.json')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    Conv(sys.argv[1], sys.argv[2]).run()
