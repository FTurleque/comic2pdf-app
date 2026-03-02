#!/usr/bin/env bash
# Lance les tests unitaires + couverture du ocr-service.
#
# Sorties : services/ocr-service/coverage.xml
#           services/ocr-service/htmlcov/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_DIR="$REPO_ROOT/services/ocr-service"

cd "$SERVICE_DIR"

# --- Créer le venv si absent ---
if [ ! -d ".venv" ]; then
    echo "  > Création du venv (.venv)..."
    python3 -m venv .venv
fi

PY=".venv/bin/python"

# --- Dépendances dev ---
echo "  > pip install -r requirements-dev.txt"
"$PY" -m pip install -q -r requirements-dev.txt

# --- Tests + couverture ---
echo "  > pytest [ocr-service]"
"$PY" -m pytest -q --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    --cov-report=html:htmlcov \
    tests

