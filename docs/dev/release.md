# Release — comic2pdf Desktop App

Ce document décrit la procédure de build et de distribution de l'application desktop
`comic2pdf-app` sous forme de **runtime portable autonome** (via `jlink`).

---

## Prérequis

| Outil | Version minimale | Vérification |
|-------|-----------------|--------------|
| JDK **complet** (avec `jmods/`) | 21 | `java --version` + `ls $JAVA_HOME/jmods` |
| Maven | 3.9+ | `mvn --version` |
| `javafx-jmods` | **21.0.4** (= `javafx.version` dans `pom.xml`) | voir ci-dessous |
| `zip` (Linux/macOS) | n/a | `zip --version` |

### Obtenir `javafx-jmods-21.0.4`

1. Aller sur <https://gluonhq.com/products/javafx/>
2. Choisir **JavaFX 21.0.4 LTS** → section **Downloads**
3. Sélectionner votre OS → **jmods** (pas SDK ni javadoc)
4. Dézipper → vous obtenez un dossier `javafx-jmods-21.0.4/` contenant des `.jmod`

> ⚠ La version **doit correspondre** à `<javafx.version>21.0.4</javafx.version>` dans
> `desktop-app/pom.xml`. Une version différente causerait une erreur `jlink`.

### Variable d'environnement requise

```bash
# Linux / macOS
export JAVAFX_JMODS_PATH=/opt/javafx-jmods-21.0.4

# Windows PowerShell
$env:JAVAFX_JMODS_PATH = "C:\tools\javafx-jmods-21.0.4"
```

---

## Build du runtime portable (jlink)

### Windows

```powershell
# Depuis la racine du dépôt
$env:JAVAFX_JMODS_PATH = "C:\tools\javafx-jmods-21.0.4"
.\scripts\package_desktop_jlink.ps1
```

Ou en passant le chemin directement :

```powershell
.\scripts\package_desktop_jlink.ps1 -JavaFxJmodsPath "C:\tools\javafx-jmods-21.0.4"
```

### Linux / macOS

```bash
export JAVAFX_JMODS_PATH=/opt/javafx-jmods-21.0.4
./scripts/package_desktop_jlink.sh
```

### Modules inclus dans le runtime

```
java.base, java.desktop, java.logging, java.naming,
java.net.http, java.xml,
javafx.controls, javafx.fxml, javafx.graphics, javafx.swing
```

> Le runtime est allégé avec `--strip-debug --compress=2 --no-header-files --no-man-pages`.

---

## Structure de l'output

Après exécution, le dossier `desktop-app/target/` contient :

```
target/
├── comic2pdf-desktop-jlink-0.1.0-windows.zip  (ou -linux.zip)
└── comic2pdf-runtime/
    ├── bin/
    │   └── java                  ← JVM minimale autonome
    ├── lib/
    ├── app/
    │   └── desktop-app-0.1.0.jar ← fat-JAR de l'application
    ├── run.bat                   ← Windows : lancer l'application
    └── run.sh                    ← Linux/macOS : lancer l'application
```

---

## Lancement

### Windows

```bat
cd comic2pdf-runtime
run.bat
```

### Linux / macOS

```bash
cd comic2pdf-runtime
./run.sh
```

### Manuel (sans script)

```bash
# Linux
./comic2pdf-runtime/bin/java -jar ./comic2pdf-runtime/app/desktop-app-0.1.0.jar

# Windows
.\comic2pdf-runtime\bin\java.exe -jar .\comic2pdf-runtime\app\desktop-app-0.1.0.jar
```

> L'application requiert que la stack Docker soit démarrée (`docker compose up -d`)
> ou qu'une URL d'orchestrateur soit configurée dans l'onglet Configuration.

---

## Distribution

Distribuer l'archive `comic2pdf-desktop-jlink-0.1.0-<os>.zip` :
- L'utilisateur dézippe → exécute `run.bat` ou `run.sh`
- Aucune installation de JDK requise côté utilisateur

---

## jpackage (étape future — installable natif)

`jpackage` génère un installable natif (`.msi` Windows, `.deb`/`.rpm` Linux, `.dmg` macOS).

### Prérequis supplémentaires

| OS | Outil requis | Lien |
|----|-------------|------|
| Windows | **WiX Toolset 3.x** | <https://wixtoolset.org/> |
| Linux | `fakeroot` + `rpm` (selon format) | via gestionnaire de paquets |
| macOS | Xcode Command Line Tools | `xcode-select --install` |

### Commande indicative (Windows `.msi`)

```powershell
# Après jlink (runtime déjà généré dans target/comic2pdf-runtime)
jpackage `
  --type msi `
  --name "Comic2PDF" `
  --app-version "0.1.0" `
  --input desktop-app/target/app `
  --main-jar desktop-app-0.1.0.jar `
  --runtime-image desktop-app/target/comic2pdf-runtime `
  --dest desktop-app/target/installer `
  --win-shortcut `
  --win-menu
```

> Cette étape n'est **pas automatisée en CI** actuellement. Elle sera ajoutée dans une PR
> dédiée `feat/jpackage-installer` une fois WiX Toolset validé sur les runners GitHub.

