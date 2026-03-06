from pathlib import Path
p = Path('.flake8')
if not p.exists():
    print('.flake8 not found')
    raise SystemExit(2)
b = p.read_bytes()
print('len=', len(b))
print('first bytes:', list(b[:4]))
if b.startswith(b'\xef\xbb\xbf'):
    p.write_bytes(b[3:])
    print('Stripped BOM from .flake8')
else:
    print('.flake8 has no BOM')

