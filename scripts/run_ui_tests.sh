#!/usr/bin/env bash
# Lance les tests UI TestFX en mode visuel (affichage requis).
# UNIQUEMENT les tests @Tag("ui"). Aucun backend Docker requis.
# Mode headless : utiliser scripts/run_ui_tests_headless.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../desktop-app"

echo "Tests UI TestFX (mode visuel) — mvn -Pui-tests test"
mvn -Pui-tests test

