#!/usr/bin/env bash
# Lance les tests unitaires + couverture des outils CLI/watch (tools/).
#
# Impose un seuil minimal de couverture (PY_COV_MIN, défaut: 60%).
# Sorties : tools/coverage.xml
#           tools/htmlcov/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_DIR="$REPO_ROOT/tools"
TESTS_DIR="$REPO_ROOT/tests/tools"

COV_MIN="${PY_COV_MIN:-60}"

cd "$TOOLS_DIR"

if [ ! -d ".venv" ]; then
    echo "  > Création du venv (.venv)..."
    python3 -m venv .venv
fi

PY=".venv/bin/python"

echo "  > pip install -r requirements-dev.txt"
"$PY" -m pip install -q -r requirements-dev.txt

echo "  > pytest [tools] (seuil couverture: ${COV_MIN}%)"
export PYTHONPATH="$REPO_ROOT"
"$PY" -m pytest -q --tb=short \
    --cov=tools \
    --cov-report=term \
    --cov-report=term-missing \
    --cov-report="xml:coverage.xml" \
    --cov-report="html:htmlcov" \
    "--cov-fail-under=${COV_MIN}" \
    "$TESTS_DIR"


