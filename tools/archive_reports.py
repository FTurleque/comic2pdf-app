#!/usr/bin/env python3
from pathlib import Path
import subprocess, hashlib
root = Path('docs/ia')
src = root / 'rapports-execution'
arch_root = root / 'archives'
arch_root.mkdir(parents=True, exist_ok=True)
from datetime import datetime
stamp = datetime.now().strftime('%Y-%m-%d')
arch_dir = arch_root / f'rapports-execution-{stamp}'
arch_dir.mkdir(exist_ok=True)
mds = sorted(src.glob('*.md'))
if not mds:
    print('No reports to archive')
    raise SystemExit(0)
for m in mds:
    target = arch_dir / m.name
    # use git mv if repository
    try:
        subprocess.run(['git','mv',str(m),str(target)], check=True)
        print('git mv', m, '->', target)
    except subprocess.CalledProcessError:
        # fallback
        m.replace(target)
        print('mv', m, '->', target)
# create manifest
manifest = arch_dir / f'ARCHIVE_MANIFEST_{stamp}.txt'
with manifest.open('w', encoding='utf-8') as f:
    for p in sorted(arch_dir.glob('*.md')):
        b = p.read_bytes()
        h = hashlib.sha256(b).hexdigest()
        f.write(f'{p.name}\t{p.stat().st_size}\t{h}\n')
print('Manifest written', manifest)
# git add manifest and commit
subprocess.run(['git','add',str(manifest)])
subprocess.run(['git','commit','-m',f'archived reports to {arch_dir.name}'])
subprocess.run(['git','push'])
print('done')

