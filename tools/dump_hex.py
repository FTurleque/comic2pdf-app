from pathlib import Path
files = [
    'docs/ia/archives/rapports-execution_20260303-225251.txt',
    'docs/ia/archives/rapports-execution-20260303-225251.zip',
    'docs/ia/archives/rapports-execution-2026-03-05/ARCHIVE_MANIFEST_2026-03-05.txt',
    'desktop-app/src/main/resources/i18n/messages_fr.properties',
    '.github/workflows/static-analysis.yml'
]
for f in files:
    p = Path(f)
    if not p.exists():
        print(f, 'MISSING')
        continue
    b = p.read_bytes()
    print(f, p.stat().st_size, 'bytes; first 8:', ' '.join(f'{x:02x}' for x in b[:8]))
    # also print startswith bom
    print('startswith_bom?', b.startswith(b'\xef\xbb\xbf'))
    print()

