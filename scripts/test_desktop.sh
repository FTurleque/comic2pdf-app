#!/usr/bin/env bash
# Lance les tests Java (JUnit 5) du desktop-app.
#
# Par défaut : mvn test (tests unitaires, tag "ui" exclu via Surefire).
# Avec --ui  : mvn test -Pui-tests (tests @Tag("ui") seulement, TestFX).
# JaCoCo génère le rapport HTML dans desktop-app/target/site/jacoco/.
#
# Usage :
#   ./scripts/test_desktop.sh
#   ./scripts/test_desktop.sh --ui
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$REPO_ROOT/desktop-app"

UI=false
for arg in "$@"; do
    case "$arg" in
        --ui) UI=true ;;
        *) echo "Option inconnue : $arg" >&2; exit 1 ;;
    esac
done

cd "$DESKTOP_DIR"

if [ "$UI" = true ]; then
    echo "  > mvn test -Pui-tests [desktop-app — tests UI TestFX]"
    mvn test -Pui-tests
else
    echo "  > mvn test [desktop-app — tests unitaires]"
    mvn test
fi

