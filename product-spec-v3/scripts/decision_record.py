#!/usr/bin/env python3
"""Decision record: makes a Product Spec reproducible from the same RD Design Specs.

A decision record is a zip delivered next to the .docx:
    content.json   every value in the Product Spec (+ "sources": fingerprints of the specs)
    decisions.md   the user's answers and every judgement call, with sources
    img/...        every image the Product Spec uses (photos, crops, drawings)

Usage:
    python3 decision_record.py stamp <content.json> <spec> [<spec> ...]
        Record name / SHA-256 / page count of each source spec into content.json.

    python3 decision_record.py check <content.json> <spec> [<spec> ...]
        Compare new specs with the recorded ones. Prints SAME / CHANGED / NEW / MISSING per
        file (matched by content first, then by department + project in the file name).
        Exit 0 if everything is SAME.

    python3 decision_record.py pack <content.json> <decisions.md> <out.zip>
        Bundle content.json, decisions.md and all referenced images (paths rewritten to img/).

    python3 decision_record.py unpack <record.zip> <work_dir>
        Extract a record so build_spec.py can rebuild from <work_dir>/content.json.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def pages(path):
    if not path.lower().endswith('.pdf'):
        return None
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
    m = re.search(r'Pages:\s+(\d+)', out)
    return int(m.group(1)) if m else None


def dept_key(name):
    m = re.search(r'(?<![A-Za-z])(OE|EE|ME|TE|SR|CTP)(?![A-Za-z])', os.path.basename(name), re.I)
    return m.group(1).upper() if m else None


def stamp(content, specs):
    d = json.load(open(content, encoding='utf-8'))
    d['sources'] = [{'file': os.path.basename(s), 'sha256': sha256(s), 'pages': pages(s)} for s in specs]
    json.dump(d, open(content, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for s in d['sources']:
        print(f"recorded {s['file']}  {s['sha256'][:12]}  pages={s['pages']}")


def check(content, specs):
    d = json.load(open(content, encoding='utf-8'))
    rec = d.get('sources', [])
    if not rec:
        print('NO SOURCES RECORDED in this content.json')
        return 2
    by_hash = {r['sha256']: r for r in rec}
    used = set()
    all_same = True
    for s in specs:
        h = sha256(s)
        if h in by_hash:
            r = by_hash[h]
            used.add(r['file'])
            note = '' if r['file'] == os.path.basename(s) else f' (recorded as {r["file"]})'
            print(f'SAME     {os.path.basename(s)}{note}')
            continue
        all_same = False
        k = dept_key(s)
        cand = [r for r in rec if r['file'] not in used and k and dept_key(r['file']) == k]
        if cand:
            used.add(cand[0]['file'])
            print(f'CHANGED  {os.path.basename(s)}  (replaces {cand[0]["file"]})')
        else:
            print(f'NEW      {os.path.basename(s)}')
    for r in rec:
        if r['file'] not in used:
            all_same = False
            print(f'MISSING  {r["file"]}  (recorded, not provided this time)')
    return 0 if all_same else 1


def _image_refs(d):
    for blk in d['body']:
        for key in ('path', 'image'):
            if isinstance(blk.get(key), str):
                yield blk, key
        if blk.get('type') == 'table':
            for row in blk['rows']:
                for cell in row:
                    if isinstance(cell, dict) and cell.get('image'):
                        yield cell, 'image'


def pack(content, decisions, out):
    base = os.path.dirname(os.path.abspath(content))
    d = json.load(open(content, encoding='utf-8'))
    tmp = out + '.dir'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, 'img'))
    names = {}
    for obj, key in _image_refs(d):
        src = obj[key] if os.path.isabs(obj[key]) else os.path.join(base, obj[key])
        if not os.path.exists(src):
            sys.exit(f'image not found: {src}')
        if src not in names:
            name = os.path.basename(src)
            stem, ext = os.path.splitext(name)
            i = 1
            while name in names.values():
                name = f'{stem}_{i}{ext}'
                i += 1
            names[src] = name
            shutil.copy(src, os.path.join(tmp, 'img', name))
        obj[key] = 'img/' + names[src]
    json.dump(d, open(os.path.join(tmp, 'content.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    shutil.copy(decisions, os.path.join(tmp, 'decisions.md'))
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(tmp):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, tmp))
    shutil.rmtree(tmp)
    print(f'{out}: content.json, decisions.md, {len(names)} images')


def unpack(zpath, work):
    os.makedirs(work, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if n.startswith('/') or '..' in n.split('/'):
                sys.exit(f'unsafe path in record: {n}')
        z.extractall(work)
    print(f'extracted to {work}: ' + ', '.join(sorted(os.listdir(work))))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == 'stamp':
        stamp(sys.argv[2], sys.argv[3:])
    elif cmd == 'check':
        sys.exit(check(sys.argv[2], sys.argv[3:]))
    elif cmd == 'pack':
        pack(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'unpack':
        unpack(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
