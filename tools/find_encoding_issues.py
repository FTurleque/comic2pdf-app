# -*- coding: utf-8 -*-
"""
Scan the repository for files that are not valid UTF-8 or contain a BOM.
Usage: python tools/find_encoding_issues.py
"""
import sys
from pathlib import Path

root = Path('.').resolve()
ignore_dirs = {'.git', 'target', 'build', 'dist', '.venv', 'venv', 'node_modules', 'out', 'bin'}
text_exts = {'.yml', '.yaml', '.md', '.txt', '.py', '.java', '.xml', '.json', '.properties', '.sh', '.ps1', '.ini', '.cfg', '.gradle', '.pom', '.csv', '.tf', '.sql', '.kt', '.scala', '.bat'}

issues = []

for p in root.rglob('*'):
    try:
        if p.is_dir():
            if p.name in ignore_dirs:
                # skip trees
                for _ in p.rglob('*'):
                    break
            continue
        if any(part in ignore_dirs for part in p.parts):
            continue
        # limit by size: skip very big files
        if p.stat().st_size > 5 * 1024 * 1024:
            continue
        ext = p.suffix.lower()
        # if extension not in text list, still attempt small files
        if ext not in text_exts and p.stat().st_size > 200*1024:
            continue
        b = p.read_bytes()
        has_bom = b.startswith(b'\xef\xbb\xbf')
        try:
            _ = b.decode('utf-8')
            if has_bom:
                issues.append((str(p), 'BOM_UTF8'))
        except Exception as e:
            # not utf-8
            issues.append((str(p), f'NOT_UTF8: {e}'))
    except Exception as e:
        # ignore permission errors
        print('skip', p, 'err', e)

if not issues:
    print('OK: no encoding issues detected (utf-8)')
    sys.exit(0)

print('Detected encoding issues:')
for path, reason in issues:
    print(path, '->', reason)

# write a small report
rep = root / 'tools' / 'encoding_issues_report.txt'
rep.write_text('\n'.join(f'{p} -> {r}' for p, r in issues), encoding='utf-8')
print('\nReport written to', rep)
sys.exit(2)

