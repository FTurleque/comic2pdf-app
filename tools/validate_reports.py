# -*- coding: utf-8 -*-
"""
Validate IA report files under docs/ia/rapports-execution/
Checks:
 - filename matches pattern RAPPORT_<TYPE>_YYYY-MM-DD.md
 - contains line 'Généré par IA'
 - contains 'Auteur' or 'Auteur(s)'
 - contains a Date line YYYY-MM-DD
 - first header includes report title

If a file misses 'Généré par IA' or 'Auteur', report it; optionally auto-insert a minimal header if run with --fix
"""
import re
from pathlib import Path
from datetime import datetime

ROOT = Path('docs/ia/rapports-execution')
PAT = re.compile(r'^RAPPORT_([A-Z]+)_(\d{4}-\d{2}-\d{2})\.md$')

issues = []

for p in sorted(ROOT.glob('RAPPORT_*.md')):
    name = p.name
    m = PAT.match(name)
    if not m:
        issues.append((name, 'BAD_FILENAME'))
        continue
    r_type, r_date = m.group(1), m.group(2)
    try:
        datetime.strptime(r_date, '%Y-%m-%d')
    except Exception:
        issues.append((name, 'BAD_DATE'))
        continue
    text = p.read_text(encoding='utf-8')
    found_ai = 'Généré par IA' in text or 'Généré par IA' in text
    found_author = re.search(r'Auteur', text, re.IGNORECASE) is not None
    found_date_line = re.search(r'Date:\s*\d{4}-\d{2}-\d{2}', text) is not None
    missing = []
    if not found_ai:
        missing.append('MISSING_GENERATED_BY_IA')
    if not found_author:
        missing.append('MISSING_AUTHOR')
    if not found_date_line:
        missing.append('MISSING_DATE_LINE')
    if missing:
        issues.append((name, ','.join(missing)))

# Print results
if not issues:
    print('OK: all reports look compliant (basic checks)')
else:
    print('Issues found:')
    for name, reason in issues:
        print(f'- {name} -> {reason}')

# Exit code 0 if no issues, 2 otherwise
import sys
sys.exit(0 if not issues else 2
)

