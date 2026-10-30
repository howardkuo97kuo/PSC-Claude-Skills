#!/usr/bin/env python3
"""Verify a built Product Specification before it is shown to the user.

Usage:
    python3 verify_spec.py <spec.docx> [--master assets/master.docx] [--render <dir>]

Prints FAIL / WARN / INFO / OK lines. Any FAIL must be fixed before delivery; every WARN must be
looked at and, if it is a real issue, listed in the concerns message to the user.

Checks
  structure   TOC links resolve; every heading is in the TOC; TOC page numbers and cover
              Total Pages match the LibreOffice-rendered PDF
  numbering   Figure / Table captions numbered 1..n without gaps; every image has a caption
  connectors  every connector in the Connector List has a pin table and vice versa;
              pin numbers in each pin table run 1..n
  wording     no department / source-document names (OE, EE, ME, TE, Design Spec);
              no placeholders (TBD, TODO, XXX, ??); empty cover fields
  level       component/module-level terms that should not appear in a product-level spec
  overview    values in the System Overview table that appear nowhere else in the document
  template    styles, numbering, headers and footers identical to the master
--render <dir> writes page JPGs and a contact sheet (contact.jpg) to look at.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import zipfile

from lxml import etree

from docx import Document
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_spec import locate  # noqa: E402

DEFAULT_MASTER = os.path.join(HERE, '..', 'assets', 'master.docx')
SOURCE_TERMS = re.compile(r'\b(OE|EE|ME|TE|O\.M\.E\.T)\b|Design Spec', re.I)
PLACEHOLDER = re.compile(r'\b(TBD|TBC|TODO|XXX)\b|\?\?')
COMPONENT_LEVEL = re.compile(
    r'Reliability|Absolute Ratings?|Precautions?|\bVIH\b|\bVIL\b|\bVOH\b|\bVOL\b|Material List|'
    r'SAP|MOQ|TDM Level|Module Level|Cover Glass Thickness|Sensor Outline', re.I)

results = []


def report(level, area, msg):
    results.append((level, area, msg))


def text_of(el):
    return ''.join(n.text or '' for n in el.iter(qn('w:t')))


def table_rows(tbl):
    return [[text_of(tc).strip() for tc in tr.findall(qn('w:tc'))] for tr in tbl.findall(qn('w:tr'))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--master', default=DEFAULT_MASTER)
    ap.add_argument('--render')
    a = ap.parse_args()

    doc = Document(a.docx)
    body = doc.element.body
    kids = list(body)

    # ---------------- structure ----------------
    anchors = [h.get(qn('w:anchor')) for h in body.iter(qn('w:hyperlink'))]
    bookmarks = {b.get(qn('w:name')) for b in body.iter(qn('w:bookmarkStart'))}
    missing = [x for x in anchors if x not in bookmarks]
    if missing:
        report('FAIL', 'structure', f'TOC links with no target: {missing}')
    headings = []
    for p in body.iter(qn('w:p')):
        st = p.find('.//' + qn('w:pStyle'))
        if st is not None and st.get(qn('w:val')) in ('Heading1', 'Heading2', 'Heading3'):
            bm = p.find(qn('w:bookmarkStart'))
            headings.append((int(st.get(qn('w:val'))[-1]), text_of(p).strip(),
                             bm.get(qn('w:name')) if bm is not None else None))
    no_bm = [h[1] for h in headings if h[2] is None]
    if no_bm:
        report('FAIL', 'structure', f'headings without bookmark (not reachable from TOC): {no_bm}')
    not_in_toc = [h[1] for h in headings if h[2] and h[2] not in anchors]
    if not_in_toc:
        report('FAIL', 'structure', f'headings missing from the TOC: {not_in_toc}')

    toc_pages = {}
    for hl in body.iter(qn('w:hyperlink')):
        m = re.search(r'(\d+)\s*$', text_of(hl))
        toc_pages[hl.get(qn('w:anchor'))] = int(m.group(1)) if m else None

    work = tempfile.mkdtemp()
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', work, a.docx],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(work, os.path.splitext(os.path.basename(a.docx))[0] + '.pdf')
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    pages = txt.split('\f')
    if pages and pages[-1].strip() == '':
        pages = pages[:-1]
    actual = locate([(lv, label, bm) for lv, label, bm in headings if bm], pages)
    wrong = [(bm, toc_pages.get(bm), actual.get(bm)) for _, _, bm in headings
             if bm and toc_pages.get(bm) != actual.get(bm)]
    if wrong:
        report('FAIL', 'structure', f'TOC page numbers differ from the rendered PDF: {wrong}')
    cover = table_rows(body.findall(qn('w:tbl'))[0])
    cover_map = {r[0].rstrip(':').strip(): r[1] for r in cover if len(r) >= 2}
    tp = cover_map.get('Total Pages', '')
    if str(len(pages)) != tp.strip():
        report('FAIL', 'structure', f'cover Total Pages = {tp!r}, rendered PDF has {len(pages)} pages')
    for k, v in cover_map.items():
        if not v.strip():
            report('WARN', 'wording', f'cover field "{k}" is empty')
    sign_rows = body.findall(qn('w:tbl'))[1].findall(qn('w:tr'))
    roles = [text_of(tc).strip() for tc in sign_rows[0].findall(qn('w:tc'))]
    for role, sig_tc, name_tc in zip(roles, sign_rows[1].findall(qn('w:tc')), sign_rows[2].findall(qn('w:tc'))):
        name = text_of(name_tc).strip()
        if not name:
            report('WARN', 'signoff', f'{role}: no name')
        if sig_tc.find('.//' + qn('w:drawing')) is not None:
            report('FAIL', 'signoff', f'{role}: signature cell must be empty (signed by hand)')

    # ---------------- numbering ----------------
    caps = {'Figure': [], 'Table': []}
    body_start = next(i for i, el in enumerate(kids)
                      if el.tag == qn('w:p') and el.find('.//' + qn('w:sectPr')) is not None
                      and i > 0 and any(text_of(k).strip() == 'Contents' for k in kids[:i]))
    for i, el in enumerate(kids):
        if el.tag != qn('w:p'):
            continue
        t = text_of(el).strip()
        m = re.match(r'^(Figure|Table)\s+(\d+)\s+[–-]', t)
        if m:
            caps[m.group(1)].append(int(m.group(2)))
        if i > body_start and el.find('.//' + qn('w:drawing')) is not None:
            prev_is_conn = kids[i - 1].tag == qn('w:p') and kids[i - 1].find('.//' + qn('w:pBdr')) is not None
            nxt = text_of(kids[i + 1]).strip() if i + 1 < len(kids) else ''
            if not prev_is_conn and not nxt.startswith('Figure '):
                report('WARN', 'numbering', f'image without a Figure caption after "{text_of(kids[i - 1]).strip()[:60]}"')
    for k, nums in caps.items():
        if nums != list(range(1, len(nums) + 1)):
            report('FAIL', 'numbering', f'{k} numbers are not 1..n in order: {nums}')

    # ---------------- connectors ----------------
    conn_list, pin_tables, conn_heading = None, {}, None
    cur_h, h_by_idx = '', {}
    for i, el in enumerate(kids):
        if el.tag == qn('w:p'):
            st = el.find('.//' + qn('w:pStyle'))
            if st is not None and st.get(qn('w:val')) in ('Heading1', 'Heading2', 'Heading3'):
                cur_h = text_of(el).strip()
        h_by_idx[i] = cur_h
    for i, el in enumerate(kids):
        if el.tag != qn('w:tbl'):
            continue
        rows = table_rows(el)
        hdr = rows[0]
        if hdr[:2] == ['No.', 'Ref.']:
            conn_list = [r[1] for r in rows[1:]]
            conn_heading = h_by_idx.get(i, '')
        if hdr[:1] == ['Pin No.']:
            cap = text_of(kids[i - 1]).strip()
            m = re.match(r'^Table\s+\d+\s+[–-]\s+(.*?)\s:\s', cap)
            ref = m.group(1) if m else cap
            # Only main-board connectors (the "Pin Assignment" heading under the Embedded Board
            # chapter, which is the one holding the Connector List) are compared with the list;
            # sub-board chapters (AC/DC, Thermal ...) have their own "Pin Assignment" and pin tables.
            in_main = 'Pin Assignment' in h_by_idx.get(i, '') and conn_list is not None and \
                h_by_idx.get(i) == conn_heading
            if in_main:
                pin_tables[ref] = rows[1:]
            nums = [r[0] for r in rows[1:]]
            if nums != [str(n) for n in range(1, len(nums) + 1)]:
                report('WARN', 'connectors', f'{ref}: pin numbers are not 1..n: {nums}')
    if conn_list is not None:
        covered = set()
        for ref in pin_tables:
            for part in re.split(r'\s*/\s*', ref):
                covered.add(re.sub(r'\s*\(.*?\)', '', part).strip())
        no_table = [r for r in conn_list if r not in covered]
        extra = [r for r in covered if r not in conn_list]
        if no_table:
            report('FAIL', 'connectors', f'in Connector List but no pin table: {no_table}')
        if extra:
            report('WARN', 'connectors', f'pin table for connector not in Connector List: {extra}')

    # ---------------- wording / level ----------------
    start = next(i for i, el in enumerate(kids) if el.tag == qn('w:p') and text_of(el).strip() == 'Contents')
    body_text = []
    for el in kids[start:]:
        for p in el.iter(qn('w:p')):
            t = text_of(p).strip()
            if t:
                body_text.append(t)
    for t in body_text:
        if SOURCE_TERMS.search(t):
            report('FAIL', 'wording', f'source/department name in text: "{t[:90]}"')
        if PLACEHOLDER.search(t):
            report('WARN', 'wording', f'placeholder left in text: "{t[:90]}"')
        if COMPONENT_LEVEL.search(t):
            report('WARN', 'level', f'possible component/module-level content: "{t[:90]}"')

    # ---------------- overview consistency ----------------
    overview = None
    for i, el in enumerate(kids):
        if el.tag == qn('w:tbl') and table_rows(el)[0][:2] == ['Category', 'Key Features']:
            overview = el
            break
    if overview is not None:
        rest = ' '.join(text_of(pp) for el in kids[start:] if el is not overview
                        for pp in el.iter(qn('w:p'))).lower()
        rest_words = set(re.findall(r'[a-z0-9.]+', rest))
        for row in table_rows(overview)[1:]:
            for tok in re.split(r'[;,]', row[1]):
                words = re.findall(r'[a-z0-9.]+', tok.lower())
                if re.search(r'\d', tok) and any(w not in rest_words for w in words):
                    report('INFO', 'overview', f'"{row[0]}: {tok.strip()}" is stated only in the '
                                               'System Overview - confirm it against its source')

    # ---------------- template fidelity ----------------
    def digest(path, name):
        with zipfile.ZipFile(path) as z:
            if name not in z.namelist():
                return None
            root = etree.fromstring(z.read(name))
            return hashlib.md5(etree.tostring(root, method='c14n')).hexdigest()
    with zipfile.ZipFile(a.master) as z:
        names = [n for n in z.namelist() if re.match(r'word/(styles|numbering|header\d+|footer\d+|settings|theme/theme1)\.xml$', n)]
    changed = [n for n in names if digest(a.master, n) != digest(a.docx, n)]
    if changed:
        report('WARN', 'template', f'parts differ from the master: {changed}')

    # ---------------- render ----------------
    if a.render:
        os.makedirs(a.render, exist_ok=True)
        subprocess.run(['pdftoppm', '-jpeg', '-r', '60', pdf, os.path.join(a.render, 'page')], check=True)
        from PIL import Image, ImageDraw
        fs = sorted(f for f in os.listdir(a.render) if f.startswith('page'))
        ims = [Image.open(os.path.join(a.render, f)) for f in fs]
        cols = 6
        w = max(i.width for i in ims) // 2
        h = max(i.height for i in ims) // 2
        sheet = Image.new('RGB', (cols * (w + 6), ((len(ims) + cols - 1) // cols) * (h + 6)), 'gray')
        for k, im in enumerate(ims):
            im = im.copy()
            im.thumbnail((w, h))
            x, y = (k % cols) * (w + 6), (k // cols) * (h + 6)
            sheet.paste(im, (x, y))
            ImageDraw.Draw(sheet).text((x + 4, y + 4), str(k + 1), fill='red')
        sheet.save(os.path.join(a.render, 'contact.jpg'), quality=85)

    n_fail = sum(1 for r in results if r[0] == 'FAIL')
    n_warn = sum(1 for r in results if r[0] == 'WARN')
    for lv, area, msg in results:
        print(f'{lv:4} [{area}] {msg}')
    print(f'OK   {len(pages)} pages, {len(headings)} headings, {len(caps["Figure"])} figures, '
          f'{len(caps["Table"])} tables, {len(pin_tables)} pin tables — {n_fail} FAIL, {n_warn} WARN')
    sys.exit(1 if n_fail else 0)


if __name__ == '__main__':
    main()
