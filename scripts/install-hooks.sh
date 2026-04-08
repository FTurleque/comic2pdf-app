#!/usr/bin/env bash
# scripts/install-hooks.sh
# Installation des Git hooks locaux pour comic2pdf-app (Linux / macOS)
#
# Usage : bash scripts/install-hooks.sh
# Prérequis : Python 3.12, Git
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "=== Installation des Git hooks — comic2pdf-app ==="

# 1. Installer pre-commit
echo ""
echo "[1/4] Installation de pre-commit..."
pip install --quiet pre-commit
echo "      ✓ pre-commit installé"

# 2. Installer les hooks pre-commit (pre-commit + commit-msg stages)
echo ""
echo "[2/4] Installation des hooks pre-commit..."
cd "$REPO_ROOT"
pre-commit install
pre-commit install --hook-type commit-msg
echo "      ✓ Hooks pre-commit installés (commit + commit-msg)"

# 3. Copier le hook pre-push dans .git/hooks/
echo ""
echo "[3/4] Installation du hook pre-push..."
cp "$REPO_ROOT/.github/hooks/pre-push" "$REPO_ROOT/.git/hooks/pre-push"
chmod +x "$REPO_ROOT/.git/hooks/pre-push"
echo "      ✓ Hook pre-push copié et rendu exécutable"

# 4. Vérification
echo ""
echo "[4/4] Vérification..."
for hook in pre-commit commit-msg pre-push; do
    if [[ -f "$REPO_ROOT/.git/hooks/$hook" ]]; then
        echo "      ✓ .git/hooks/$hook"
    else
        echo "      ✗ .git/hooks/$hook manquant" >&2
    fi
done

echo ""
echo "=== Hooks installés avec succès ==="
echo ""
echo "  • pre-commit  : black --check, flake8, trailing-whitespace, check-yaml"
echo "  • commit-msg  : validation Conventional Commits"
echo "  • pre-push    : pytest sur les services Python modifiés"
echo ""
echo "  Ignorer ponctuellement : git commit --no-verify / git push --no-verify"
echo ""
