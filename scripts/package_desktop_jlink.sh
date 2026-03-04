#!/usr/bin/env bash
# =============================================================================
# package_desktop_jlink.sh
# Crée un runtime portable jlink + fat-JAR pour l'application desktop comic2pdf.
#
# Étapes :
#   1. Compile et package le fat-JAR via Maven (mvn package -DskipTests).
#   2. Génère un runtime Java minimal via jlink (modules JDK + JavaFX).
#   3. Copie le JAR dans le runtime.
#   4. Génère un script run.sh de lancement.
#   5. Zippe le tout dans comic2pdf-desktop-jlink-0.1.0-linux.zip.
#
# Prérequis :
#   - JDK 21 FULL avec $JAVA_HOME/jmods/ présent (pas un JRE)
#   - Maven 3.9+
#   - javafx-jmods-21.0.4 (https://gluonhq.com/products/javafx/)
#   - Variable JAVAFX_JMODS_PATH pointant vers le dossier des jmods JavaFX
#
# Usage :
#   JAVAFX_JMODS_PATH=/opt/javafx-jmods-21.0.4 ./scripts/package_desktop_jlink.sh
#   export JAVAFX_JMODS_PATH=/opt/javafx-jmods-21.0.4 && ./scripts/package_desktop_jlink.sh
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Vérifications prérequis
# ---------------------------------------------------------------------------

JAVAFX_JMODS_PATH="${JAVAFX_JMODS_PATH:-}"

if [[ -z "$JAVAFX_JMODS_PATH" ]]; then
    echo "❌ Variable JAVAFX_JMODS_PATH non definie." >&2
    echo "   Telecharger javafx-jmods-21.0.4 depuis https://gluonhq.com/products/javafx/" >&2
    echo "   Puis : export JAVAFX_JMODS_PATH=/chemin/javafx-jmods-21.0.4" >&2
    exit 1
fi

if [[ ! -d "$JAVAFX_JMODS_PATH" ]]; then
    echo "❌ Dossier javafx-jmods introuvable : $JAVAFX_JMODS_PATH" >&2
    exit 1
fi

if [[ -z "${JAVA_HOME:-}" ]]; then
    echo "❌ Variable JAVA_HOME non definie. JDK 21 complet requis." >&2
    exit 1
fi

if [[ ! -d "$JAVA_HOME/jmods" ]]; then
    echo "❌ Dossier $JAVA_HOME/jmods absent. JDK complet (pas JRE) requis." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$REPO_ROOT/desktop-app"
TARGET_DIR="$DESKTOP_DIR/target"
RUNTIME_DIR="$TARGET_DIR/comic2pdf-runtime"
APP_DIR="$RUNTIME_DIR/app"
JAR_NAME="desktop-app-0.1.0.jar"
JAR_SOURCE="$TARGET_DIR/$JAR_NAME"
ZIP_OUTPUT="$TARGET_DIR/comic2pdf-desktop-jlink-0.1.0-linux.zip"

MODULES="java.base,java.desktop,java.logging,java.naming,java.net.http,java.xml,javafx.controls,javafx.fxml,javafx.graphics,javafx.swing"

# ---------------------------------------------------------------------------
# Étape 1 : Build Maven
# ---------------------------------------------------------------------------

echo "==> Build Maven (package -DskipTests)..."
cd "$DESKTOP_DIR"
mvn -q -DskipTests package

if [[ ! -f "$JAR_SOURCE" ]]; then
    echo "❌ JAR introuvable apres build : $JAR_SOURCE" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Étape 2 : jlink — génération du runtime minimal
# ---------------------------------------------------------------------------

echo "==> jlink : generation du runtime ($RUNTIME_DIR)..."

if [[ -d "$RUNTIME_DIR" ]]; then
    rm -rf "$RUNTIME_DIR"
fi

"$JAVA_HOME/bin/jlink" \
    --module-path "$JAVA_HOME/jmods:$JAVAFX_JMODS_PATH" \
    --add-modules "$MODULES" \
    --output "$RUNTIME_DIR" \
    --strip-debug \
    --compress=2 \
    --no-header-files \
    --no-man-pages

# ---------------------------------------------------------------------------
# Étape 3 : Copie du JAR dans le runtime
# ---------------------------------------------------------------------------

echo "==> Copie du JAR dans $APP_DIR..."
mkdir -p "$APP_DIR"
cp "$JAR_SOURCE" "$APP_DIR/$JAR_NAME"

# ---------------------------------------------------------------------------
# Étape 4 : Script de lancement run.sh
# ---------------------------------------------------------------------------

echo "==> Generation de run.sh..."
cat > "$RUNTIME_DIR/run.sh" << 'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/bin/java" -jar "$SCRIPT_DIR/app/desktop-app-0.1.0.jar" "$@"
EOF
chmod +x "$RUNTIME_DIR/run.sh"

# ---------------------------------------------------------------------------
# Étape 5 : Archive ZIP
# ---------------------------------------------------------------------------

echo "==> Creation de l'archive ZIP..."
if [[ -f "$ZIP_OUTPUT" ]]; then
    rm -f "$ZIP_OUTPUT"
fi

cd "$TARGET_DIR"
zip -r "$(basename "$ZIP_OUTPUT")" "$(basename "$RUNTIME_DIR")"

echo ""
echo "✅ Packaging termine !"
echo "   Archive : $ZIP_OUTPUT"
echo "   Lancement : dezipper puis executer ./comic2pdf-runtime/run.sh"

