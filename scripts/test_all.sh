#!/usr/bin/env bash
# Lance tous les tests du projet comic2pdf-app (Python + Java).
#
# Enchaîne les 4 scripts de test individuels :
#   1. scripts/test_prep.sh         — pytest + coverage (prep-service)
#   2. scripts/test_ocr.sh          — pytest + coverage (ocr-service)
#   3. scripts/test_orchestrator.sh — pytest + coverage (orchestrator)
#   4. scripts/test_desktop.sh      — mvn test (desktop-app, sans UI)
#
# Par défaut : s'arrête au premier échec.
# Avec --continue-on-error : exécute tout et affiche un résumé final.
#
# Usage :
#   ./scripts/test_all.sh
#   ./scripts/test_all.sh --continue-on-error
#
# Rapports coverage Python : services/<service>/coverage.xml + htmlcov/
# Rapport JaCoCo Java      : desktop-app/target/site/jacoco/index.html
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

CONTINUE_ON_ERROR=false
for arg in "$@"; do
    case "$arg" in
        --continue-on-error) CONTINUE_ON_ERROR=true ;;
        *) echo "Option inconnue : $arg" >&2; exit 1 ;;
    esac
done

FAILURES=()

# Couleurs (désactivées si pas de terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
    YELLOW='\033[0;33m'; RESET='\033[0m'
else
    RED=''; GREEN=''; CYAN=''; YELLOW=''; RESET=''
fi

header() {
    echo ""
    echo -e "${CYAN}============================================================${RESET}"
    echo -e "${CYAN}  $1${RESET}"
    echo -e "${CYAN}============================================================${RESET}"
}

run_step() {
    local name="$1"
    local script="$2"
    header "$name"
    bash "$script"
    local rc=$?
    if [ $rc -ne 0 ]; then
        FAILURES+=("$name")
        if [ "$CONTINUE_ON_ERROR" = false ]; then
            echo ""
            echo -e "${RED}  ECHEC : $name (exit $rc)${RESET}"
            echo -e "${YELLOW}  Arrêt. Utiliser --continue-on-error pour tout exécuter.${RESET}"
            exit 1
        fi
    fi
}

# ---------------------------------------------------------------------------
# Exécution séquentielle
# ---------------------------------------------------------------------------
run_step "prep-service"          "$SCRIPT_DIR/test_prep.sh"
run_step "ocr-service"           "$SCRIPT_DIR/test_ocr.sh"
run_step "orchestrator"          "$SCRIPT_DIR/test_orchestrator.sh"
run_step "desktop-app (mvn)"     "$SCRIPT_DIR/test_desktop.sh"

# ---------------------------------------------------------------------------
# Résumé final
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}============================================================${RESET}"
echo -e "${CYAN}  RESUME GLOBAL${RESET}"
echo -e "${CYAN}============================================================${RESET}"

ALL_STEPS=("prep-service" "ocr-service" "orchestrator" "desktop-app (mvn)")
for step in "${ALL_STEPS[@]}"; do
    failed=false
    for f in "${FAILURES[@]+"${FAILURES[@]}"}"; do
        [ "$f" = "$step" ] && failed=true && break
    done
    if [ "$failed" = true ]; then
        printf "${RED}  %-40s [FAIL]${RESET}\n" "$step"
    else
        printf "${GREEN}  %-40s [PASS]${RESET}\n" "$step"
    fi
done
echo ""

if [ ${#FAILURES[@]} -gt 0 ]; then
    echo -e "${RED}  RESULTAT GLOBAL : ECHEC ($(IFS=', '; echo "${FAILURES[*]}"))${RESET}"
    echo ""
    exit 1
fi

echo -e "${GREEN}  RESULTAT GLOBAL : SUCCES${RESET}"
echo ""
exit 0

