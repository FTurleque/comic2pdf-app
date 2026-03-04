<#
.SYNOPSIS
    Crée un runtime portable jlink + fat-JAR pour l'application desktop comic2pdf.

.DESCRIPTION
    1. Compile et package le fat-JAR via Maven (mvn package -DskipTests).
    2. Génère un runtime Java minimal via jlink (modules JDK + JavaFX).
    3. Copie le JAR dans le runtime.
    4. Génère un script run.bat de lancement.
    5. Zippe le tout dans comic2pdf-desktop-jlink-0.1.0-windows.zip.

.PARAMETER JavaFxJmodsPath
    Chemin vers le dossier javafx-jmods-21.0.4 (contient javafx.controls.jmod, etc.).
    Télécharger depuis : https://gluonhq.com/products/javafx/ (SDK zip > jmods/).
    Si non fourni, utilise la variable d'environnement JAVAFX_JMODS_PATH.

.NOTES
    Prérequis :
    - JDK 21 FULL (avec $env:JAVA_HOME/jmods/ présent, pas un JRE)
    - Maven 3.9+
    - javafx-jmods-21.0.4 correspondant à javafx.version=21.0.4 dans pom.xml
    - Variable JAVAFX_JMODS_PATH ou paramètre -JavaFxJmodsPath

.EXAMPLE
    .\scripts\package_desktop_jlink.ps1 -JavaFxJmodsPath "C:\tools\javafx-jmods-21.0.4"

.EXAMPLE
    $env:JAVAFX_JMODS_PATH = "C:\tools\javafx-jmods-21.0.4"
    .\scripts\package_desktop_jlink.ps1
#>
param(
    [string]$JavaFxJmodsPath = $env:JAVAFX_JMODS_PATH
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Vérifications prérequis
# ---------------------------------------------------------------------------

if ([string]::IsNullOrWhiteSpace($JavaFxJmodsPath)) {
    Write-Error @"
Parametre JavaFxJmodsPath manquant.
Fournir via -JavaFxJmodsPath ou la variable d'environnement JAVAFX_JMODS_PATH.
Exemple : .\scripts\package_desktop_jlink.ps1 -JavaFxJmodsPath "C:\tools\javafx-jmods-21.0.4"
Telecharger depuis : https://gluonhq.com/products/javafx/
"@
}

if (-not (Test-Path $JavaFxJmodsPath)) {
    Write-Error "Dossier javafx-jmods introuvable : $JavaFxJmodsPath"
}

if ([string]::IsNullOrWhiteSpace($env:JAVA_HOME)) {
    Write-Error "Variable JAVA_HOME non definie. JDK 21 complet requis (avec jmods/)."
}

$jdkJmods = Join-Path $env:JAVA_HOME "jmods"
if (-not (Test-Path $jdkJmods)) {
    Write-Error "Dossier jmods absent dans JAVA_HOME ($jdkJmods). JDK complet (pas JRE) requis."
}

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot    = Split-Path -Parent $scriptDir
$desktopDir  = Join-Path $repoRoot "desktop-app"
$targetDir   = Join-Path $desktopDir "target"
$runtimeDir  = Join-Path $targetDir "comic2pdf-runtime"
$appDir      = Join-Path $runtimeDir "app"
$jarName     = "desktop-app-0.1.0.jar"
$jarSource   = Join-Path $targetDir $jarName
$zipOutput   = Join-Path $targetDir "comic2pdf-desktop-jlink-0.1.0-windows.zip"

$modules = "java.base,java.desktop,java.logging,java.naming,java.net.http,java.xml," +
           "javafx.controls,javafx.fxml,javafx.graphics,javafx.swing"

# ---------------------------------------------------------------------------
# Étape 1 : Build Maven
# ---------------------------------------------------------------------------

Write-Host "==> Build Maven (package -DskipTests)..." -ForegroundColor Cyan
Push-Location $desktopDir
try {
    & mvn -q -DskipTests package
    if ($LASTEXITCODE -ne 0) { throw "mvn package a echoue (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

if (-not (Test-Path $jarSource)) {
    Write-Error "JAR introuvable apres build : $jarSource"
}

# ---------------------------------------------------------------------------
# Étape 2 : jlink — génération du runtime minimal
# ---------------------------------------------------------------------------

Write-Host "==> jlink : generation du runtime ($runtimeDir)..." -ForegroundColor Cyan

if (Test-Path $runtimeDir) {
    Remove-Item $runtimeDir -Recurse -Force
}

$jlink = Join-Path $env:JAVA_HOME "bin\jlink.exe"
& $jlink `
    --module-path "$jdkJmods;$JavaFxJmodsPath" `
    --add-modules $modules `
    --output $runtimeDir `
    --strip-debug `
    --compress=2 `
    --no-header-files `
    --no-man-pages

if ($LASTEXITCODE -ne 0) { throw "jlink a echoue (exit $LASTEXITCODE)" }

# ---------------------------------------------------------------------------
# Étape 3 : Copie du JAR dans le runtime
# ---------------------------------------------------------------------------

Write-Host "==> Copie du JAR dans $appDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $appDir -Force | Out-Null
Copy-Item $jarSource (Join-Path $appDir $jarName)

# ---------------------------------------------------------------------------
# Étape 4 : Script de lancement run.bat
# ---------------------------------------------------------------------------

Write-Host "==> Generation de run.bat..." -ForegroundColor Cyan
$runBatContent = @"
@echo off
"%~dp0bin\java" -jar "%~dp0app\$jarName" %*
"@
$runBatContent | Set-Content -Path (Join-Path $runtimeDir "run.bat") -Encoding ASCII

# ---------------------------------------------------------------------------
# Étape 5 : Archive ZIP
# ---------------------------------------------------------------------------

Write-Host "==> Creation de l'archive ZIP..." -ForegroundColor Cyan
if (Test-Path $zipOutput) { Remove-Item $zipOutput -Force }

Compress-Archive -Path $runtimeDir -DestinationPath $zipOutput -Force

Write-Host ""
Write-Host "✅ Packaging termine !" -ForegroundColor Green
Write-Host "   Archive : $zipOutput"
Write-Host "   Lancement : dezipper puis executer run.bat"

