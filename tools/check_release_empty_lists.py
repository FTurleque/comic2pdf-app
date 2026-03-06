# -*- coding: utf-8 -*-
import yaml

def find_empty_lists(node, path=""):
    found = []
    if isinstance(node, list):
        if len(node) == 0:
            found.append((path or "<root>", node))
        for i, item in enumerate(node):
            found += find_empty_lists(item, f"{path}[{i}]")
    elif isinstance(node, dict):
        for k, v in node.items():
            new_path = f"{path}.{k}" if path else k
            found += find_empty_lists(v, new_path)
    return found

with open('.github/workflows/release.yml', 'r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)

empties = find_empty_lists(data)
if not empties:
    print('No empty lists found in release.yml')
else:
    print(f'Found {len(empties)} empty lists:')
    for p, val in empties:
        print(' -', p, '->', val)

