from pathlib import Path
files = [
    'desktop-app/src/main/resources/i18n/messages_fr.properties',
    '.github/workflows/static-analysis.yml',
    'docs/ia/archives/rapports-execution_20260303-225251.txt',
    'docs/ia/archives/rapports-execution-20260303-225251.zip',
    'docs/ia/archives/rapports-execution-2026-03-05/ARCHIVE_MANIFEST_2026-03-05.txt'
]
for f in files:
    p=Path(f)
    if not p.exists():
        print(f, 'MISSING')
        continue
    b=p.read_bytes()
    print('\nFILE:', f)
    print('size:', len(b))
    print('first 16 bytes:', ' '.join(f'{x:02x}' for x in b[:16]))
    # print first 16 as decimal
    print('first 16 dec:', ' '.join(str(x) for x in b[:16]))
    # check common BOMs
    print('starts with UTF8 BOM EF BB BF?', b.startswith(b'\xef\xbb\xbf'))
    print('starts with UTF-16 LE BOM FF FE?', b.startswith(b'\xff\xfe'))
    print('starts with UTF-16 BE BOM FE FF?', b.startswith(b'\xfe\xff'))

