#!/usr/bin/env python3
"""Validateur de message de commit (Conventional Commits).

Invoqué par pre-commit au stage commit-msg.
Le fichier contenant le message de commit est passé en premier argument.
"""

import re
import sys

# Types autorisés (source : .github/git-commit-instructions.md)
_TYPES = "feat|fix|refactor|perf|test|docs|build|chore|ci|revert"

# Format : <type>(<scope>)?(!)?:_<sujet_1_à_100_chars>
_PATTERN = re.compile(
    rf"^({_TYPES})"
    r"(\([a-z0-9,/_-]+\))?"
    r"(!)?"
    r": "
    r".{1,100}$"
)

_TYPES_HINT = "feat | fix | refactor | perf | test | docs | build | chore | ci | revert"
_SCOPES_HINT = (
    "desktop | orchestrator | prep-service | ocr-service | docker | docs | tests | config"
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: commit-msg-validator.py <commit-msg-file>", file=sys.stderr)
        return 1

    with open(sys.argv[1], encoding="utf-8") as fh:
        first_line = fh.readline().strip()

    # Ignorer les commits générés automatiquement par Git
    if first_line.startswith(("Merge ", "Revert ", "fixup! ", "squash! ")):
        return 0

    if _PATTERN.match(first_line):
        return 0

    print(f"\n✗ Message de commit invalide :\n  {first_line!r}", file=sys.stderr)
    print(f"\n  Format attendu   : <type>(<scope>): <sujet>", file=sys.stderr)
    print(f"  Types autorisés  : {_TYPES_HINT}", file=sys.stderr)
    print(f"  Scopes conseillés: {_SCOPES_HINT}", file=sys.stderr)
    print(f"\n  Exemple valide   : feat(orchestrator): ajouter heartbeat timeout\n", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
