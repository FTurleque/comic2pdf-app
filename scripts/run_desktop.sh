#!/usr/bin/env bash
# Lance l'application desktop JavaFX Comic2PDF.
# ORCHESTRATOR_URL est lu via System.getenv() par l'application.
# Prérequis : stack Docker démarrée (scripts/dev_up.sh), Java 21, Maven 3.9+
set -e

export ORCHESTRATOR_URL="http://localhost:18083"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../desktop-app"

echo "ORCHESTRATOR_URL=$ORCHESTRATOR_URL"
echo "Lancement de l'UI desktop via mvn javafx:run ..."
mvn -q javafx:run

