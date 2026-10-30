#!/usr/bin/env python3
"""Render one PDF page at high resolution and crop it to the drawing/figure on it.

Usage:
    python3 crop_page.py <pdf> <page> <out.png> [--dpi 250] [--rotate cw|ccw|none]
                         [--box x0,y0,x1,y1] [--skip-top 0.09] [--skip-bottom 0.07]

  --box         crop box as fractions of the page (0-1); default: auto-trim to non-white
                content after skipping the header/footer bands.
  --rotate      ME drawings are often placed sideways on a portrait page; 'cw' turns a
                drawing whose title block sits at the top-right back to landscape.

Use it for drawings that are vector (WMF/EMF) in the source and therefore not
extractable with pdfimages, e.g. ME outline / explode / package drawings.
Always look at the result before using it.
"""
import argparse
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('page', type=int)
    ap.add_argument('out')
    ap.add_argument('--dpi', type=int, default=250)
    ap.add_argument('--rotate', default='none', choices=['cw', 'ccw', 'none'])
    ap.add_argument('--box')
    ap.add_argument('--skip-top', type=float, default=0.09)
    ap.add_argument('--skip-bottom', type=float, default=0.07)
    a = ap.parse_args()
    work = tempfile.mkdtemp()
    stem = os.path.join(work, 'pg')
    subprocess.run(['pdftoppm', '-png', '-r', str(a.dpi), '-f', str(a.page), '-l', str(a.page),
                    '-singlefile', a.pdf, stem], check=True)
    im = Image.open(stem + '.png').convert('RGB')
    W, H = im.size
    if a.box:
        x0, y0, x1, y1 = [float(v) for v in a.box.split(',')]
        im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    else:
        top, bottom = int(a.skip_top * H), int((1 - a.skip_bottom) * H)
        band = np.asarray(im)[top:bottom].astype(int)
        # engineering drawings have a border frame: crop to it when one is found.
        # Search the whole page (the frame can reach into the footer band).
        dark = np.asarray(im).astype(int).sum(2) < 600          # frame lines may be grey

        def longest_run(v):
            """(length, start, end) of the longest run of True values."""
            best = (0, 0, 0)
            cur, start = 0, 0
            for i, x in enumerate(v):
                if x:
                    if cur == 0:
                        start = i
                    cur += 1
                    if cur > best[0]:
                        best = (cur, start, i)
                else:
                    cur = 0
            return best
        # a frame line is one continuous stroke (text rows have gaps between letters);
        # the frame box is the extent of all such strokes, so 3 drawn edges are enough
        xs, ys, n = [], [], 0
        for y in np.where(dark.mean(1) > 0.45)[0]:
            ln, s0, s1 = longest_run(dark[y])
            if ln > 0.4 * W:
                ys.append(y); xs += [s0, s1]; n += 1
        for x in np.where(dark.mean(0) > 0.45)[0]:
            ln, s0, s1 = longest_run(dark[:, x])
            if ln > 0.4 * H:
                xs.append(x); ys += [s0, s1]; n += 1
        if n >= 3 and max(xs) - min(xs) > 0.3 * W and max(ys) - min(ys) > 0.3 * H:
            pad = 4
            im = im.crop((max(min(xs) - pad, 0), max(min(ys) - pad, 0),
                          min(max(xs) + pad, W), min(max(ys) + pad, H)))
            if a.rotate == 'cw':
                im = im.rotate(-90, expand=True)
            elif a.rotate == 'ccw':
                im = im.rotate(90, expand=True)
            im.save(a.out)
            print(a.out, im.size, '(frame)')
            return
        nonwhite = band.sum(2) < 700
        ys, xs = np.where(nonwhite)
        if len(ys) == 0:
            raise SystemExit('page is blank in the selected band')
        pad = 6
        im = im.crop((max(xs.min() - pad, 0), top + max(ys.min() - pad, 0),
                      min(xs.max() + pad, W), top + min(ys.max() + pad, bottom - top)))
    if a.rotate == 'cw':
        im = im.rotate(-90, expand=True)
    elif a.rotate == 'ccw':
        im = im.rotate(90, expand=True)
    im.save(a.out)
    print(a.out, im.size)


if __name__ == '__main__':
    main()
