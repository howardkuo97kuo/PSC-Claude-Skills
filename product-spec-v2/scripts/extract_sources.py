#!/usr/bin/env python3
"""Extract text and images from the four O/M/E/T Design Specs.

Usage:
    python3 extract_sources.py <out_dir> <spec1> [<spec2> ...]

For every input (.pdf / .doc / .docx):
  <out_dir>/<stem>/text.txt          layout text (pdftotext -layout)
  <out_dir>/<stem>/pages/p-NN.jpg    page renders (for reading drawings/images)
  <out_dir>/<stem>/images/*.png      embedded images (pdfimages -png -p)
  <out_dir>/<stem>/crops/*.png       auto-cropped connector drawings (EE pin tables)
  <out_dir>/<stem>/contact.jpg       contact sheet of all embedded images, labelled

.doc/.docx inputs are converted to PDF with LibreOffice first.
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def to_pdf(path, work):
    if path.lower().endswith('.pdf'):
        return path
    run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', work, path])
    pdf = os.path.join(work, os.path.splitext(os.path.basename(path))[0] + '.pdf')
    if not os.path.exists(pdf):
        sys.exit(f'LibreOffice could not convert {path}')
    return pdf


def crop_connector(png_path):
    """Return the connector drawing cropped out of an EE pin-table image, or None.

    EE pin tables are one embedded image: title row, connector drawing, then a
    light-green 'Pin No. | Pin Name | Description' header row. The drawing is the
    band between the title row's bottom border and the green header row.
    """
    im = Image.open(png_path).convert('RGB')
    a = np.asarray(im).astype(int)
    h, w, _ = a.shape
    if h < 60 or w < 60:
        return None
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > 200) & (g - r > 15) & (g - b > 15)
    dark = a.sum(2) < 300
    green_rows = np.where(green.mean(1) > 0.5)[0]
    if len(green_rows) == 0:
        return None
    gtop = int(green_rows[0])
    line_rows = [y for y in range(gtop) if dark[y].mean() > 0.6]
    # group consecutive line rows
    groups = []
    for y in line_rows:
        if groups and y - groups[-1][-1] <= 2:
            groups[-1].append(y)
        else:
            groups.append([y])
    if len(groups) >= 3:
        top = groups[1][-1] + 2          # below title row
        bottom = groups[-1][0] - 2       # above line on top of green row
    elif len(groups) == 2:
        top = groups[0][-1] + 2
        bottom = groups[-1][0] - 2
    else:
        top, bottom = 0, gtop - 2
    if bottom - top < 20:
        return None
    region = a[top:bottom].copy()
    # blank out table border lines (columns/rows that are mostly dark)
    # only near the left/right/top/bottom edges, so pins inside the drawing stay
    dk = region.sum(2) < 380
    rh, rw = dk.shape
    edge = max(8, rw // 25)
    for x in list(range(min(edge, rw))) + list(range(max(rw - edge, 0), rw)):
        if dk[:, x].mean() > 0.45:
            region[:, x] = 255
    edge_y = max(4, rh // 25)
    for y in list(range(min(edge_y, rh))) + list(range(max(rh - edge_y, 0), rh)):
        if dk[y].mean() > 0.6:
            region[y] = 255
    nonwhite = region.sum(2) < 690
    ys, xs = np.where(nonwhite)
    if len(ys) == 0:
        return None
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, region.shape[0] - 1)
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, region.shape[1] - 1)
    return Image.fromarray(region[y0:y1 + 1, x0:x1 + 1].astype('uint8'))


CONN_TITLE = __import__('re').compile(r'^\s*(J|CN|CON|P)\d+[\w-]*\s*(&\s*\w+\s*)?(/\s*\w+\s*)?:', __import__('re').M)


def is_table_image(png_path):
    """True if the image looks like a table (several full-width horizontal rules)."""
    a = np.asarray(Image.open(png_path).convert('RGB')).astype(int)
    dark = a.sum(2) < 380
    rows = np.where(dark.mean(1) > 0.95)[0]      # full-width rules only
    groups = 0
    prev = -10
    for y in rows:
        if y - prev > 2:
            groups += 1
        prev = y
    return groups >= 4


def trim_whitespace(png_path):
    im = Image.open(png_path).convert('RGB')
    a = np.asarray(im).astype(int)
    ys, xs = np.where(a.sum(2) < 690)
    if len(ys) == 0:
        return None
    pad = 4
    return im.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0),
                    min(xs.max() + pad, im.width), min(ys.max() + pad, im.height)))


def contact_sheet(paths, out, thumb=220, cols=6):
    if not paths:
        return
    cells = []
    for p in paths:
        im = Image.open(p).convert('RGB')
        im.thumbnail((thumb, thumb))
        cell = Image.new('RGB', (thumb, thumb + 18), 'white')
        cell.paste(im, ((thumb - im.width) // 2, 0))
        ImageDraw.Draw(cell).text((4, thumb + 3), os.path.basename(p), fill='red')
        cells.append(cell)
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (thumb + 6), rows * (thumb + 24)), 'white')
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % cols) * (thumb + 6), (i // cols) * (thumb + 24)))
    sheet.save(out, quality=85)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    for src in sys.argv[2:]:
        stem = os.path.splitext(os.path.basename(src))[0]
        d = os.path.join(out_dir, stem)
        for sub in ('pages', 'images', 'crops'):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        pdf = to_pdf(src, d)
        run(['pdftotext', '-layout', pdf, os.path.join(d, 'text.txt')])
        run(['pdftoppm', '-jpeg', '-r', '110', pdf, os.path.join(d, 'pages', 'p')])
        run(['pdfimages', '-png', '-p', pdf, os.path.join(d, 'images', 'img')])
        imgs = sorted(os.path.join(d, 'images', f) for f in os.listdir(os.path.join(d, 'images')))
        # drop the page-header logo (same size repeated on most pages) and tiny images
        from collections import Counter
        sizes = {}
        for p in imgs:
            with Image.open(p) as im:
                sizes[p] = im.size
        n_pages_pdf = len(os.listdir(os.path.join(d, 'pages')))
        common = {sz for sz, c in Counter(sizes.values()).items() if c >= max(3, n_pages_pdf // 2)}
        keep = [p for p in imgs if sizes[p] not in common and sizes[p][0] * sizes[p][1] >= 6000]
        # page text, to know which pages carry connector pin assignments
        page_txt = open(os.path.join(d, 'text.txt'), encoding='utf-8', errors='ignore').read().split('')
        crops = []
        for p in keep:
            # format A: drawing + pin table in one image (green header row) -> cut the drawing out
            c = crop_connector(p)
            if c is None:
                # format B: drawing and pin table are separate images -> keep the non-table
                # images found on pages that have connector titles ("CON3:", "J7 :", ...)
                m = __import__('re').search(r'img-(\d+)-', os.path.basename(p))
                pg = int(m.group(1)) if m else 0
                txt = page_txt[pg - 1] if 0 < pg <= len(page_txt) else ''
                with Image.open(p) as im:
                    small = im.width < 1200 and im.height < 1200
                if small and CONN_TITLE.search(txt) and not is_table_image(p):
                    c = trim_whitespace(p)
            if c is not None:
                cp = os.path.join(d, 'crops', os.path.basename(p))
                c.save(cp)
                crops.append(cp)
        contact_sheet(keep, os.path.join(d, 'contact.jpg'))
        contact_sheet(crops, os.path.join(d, 'crops_contact.jpg'))
        n_pages = len(os.listdir(os.path.join(d, 'pages')))
        print(f'{stem}: {n_pages} pages, {len(keep)} images, {len(crops)} connector crops -> {d}')


if __name__ == '__main__':
    main()
