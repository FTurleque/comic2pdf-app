import subprocess, sys
p = subprocess.run(['git', 'ls-files', 'docs/ia/rapports-execution'], capture_output=True, text=True)
if p.returncode != 0:
    print('git ls-files returned non-zero, output:')
    print(p.stderr)
    sys.exit(2)
out = p.stdout.strip()
if not out:
    print('NO_TRACKED_FILES')
else:
    print('TRACKED_FILES:\n', out)

