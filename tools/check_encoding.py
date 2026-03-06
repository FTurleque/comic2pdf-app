# -*- coding: utf-8 -*-
"""
Vérifie l'encodage UTF-8 et la présence éventuelle d'un BOM pour le fichier donné.
Usage: python tools/check_encoding.py .github/workflows/python-quality.yml
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Usage: python tools/check_encoding.py <path>')
    sys.exit(2)

p = Path(sys.argv[1])
if not p.exists():
    print('File not found:', p)
    sys.exit(2)

b = p.read_bytes()
print('Path:', p)
print('Size bytes:', len(b))
print('First 8 bytes (hex):', ' '.join(f'{c:02x}' for c in b[:8]))
# BOM UTF-8 is 0xEF 0xBB 0xBF
bom = b.startswith(b'\xef\xbb\xbf')
print('Has UTF-8 BOM:', bom)
try:
    s = b.decode('utf-8')
    print('UTF-8 decode: OK')
    # Print first 3 lines
    lines = s.splitlines()
    for i, line in enumerate(lines[:5]):
        print(f'Line {i+1}:', line)
except Exception as e:
    print('UTF-8 decode: ERROR:', e)
    # attempt latin-1 decode
    try:
        s = b.decode('latin-1')
        print('Latin-1 decode OK, first line:', s.splitlines()[0])
    except Exception:
        pass

