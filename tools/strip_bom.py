# -*- coding: utf-8 -*-
"""
Strip UTF-8 BOM (0xEF 0xBB 0xBF) occurrences from text files under the repo.
Only operates on a safe list of text extensions to avoid corrupting binary files.
Usage: python tools/strip_bom.py
"""
from pathlib import Path

TEXT_EXTS = {'.yml', '.yaml', '.md', '.txt', '.properties', '.py', '.ini', '.cfg', '.json', '.xml'}
root = Path('.').resolve()
count = 0
for p in root.rglob('*'):
    try:
        if p.is_dir():
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        b = p.read_bytes()
        if b.find(b'\xef\xbb\xbf') != -1:
            newb = b.replace(b'\xef\xbb\xbf', b'')
            p.write_bytes(newb)
            print('Stripped BOM from', p)
            count += 1
    except Exception as e:
        print('skip', p, e)

print('Done. files modified:', count)

