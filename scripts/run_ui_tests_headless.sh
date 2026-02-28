#!/usr/bin/env bash
# Lance les tests UI TestFX en mode headless (sans affichage — Monocle).
# Si toujours pas d'affichage : ajouter -Dglass.platform=Monocle -Dmonocle.platform=Headless
# Si InaccessibleObjectException sur com.sun.net.httpserver (rare Java 21) :
#   ajouter --add-exports jdk.httpserver/com.sun.net.httpserver=ALL-UNNAMED dans pom.xml ui-tests argLine
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../desktop-app"

echo "Tests UI TestFX (mode headless Monocle)"
mvn -Pui-tests test \
    -Dtestfx.headless=true \
    -Dprism.order=sw \
    -Dprism.verbose=true

