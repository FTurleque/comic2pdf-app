# Setup développeur — comic2pdf-app

Ce guide couvre l'installation de l'environnement de développement complet pour travailler sur `comic2pdf-app`.

---

## Prérequis logiciels

| Logiciel | Version | Vérification |
|---|---|---|
| Python | 3.12 | `python --version` |
| pip | dernière | `pip --version` |
| Java (JDK) | 21 | `java --version` |
| Maven | 3.9+ | `mvn --version` |
| Docker Desktop / Engine | 4.x / 24+ | `docker --version` |
| Git | 2.x | `git --version` |

---

## Setup Python 3.12 + venv par service

Chaque service Python doit avoir son propre environnement virtuel pour isoler les dépendances.

### Windows (PowerShell)

```powershell
# prep-service
cd services\prep-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# Vérifier :
pytest -q
deactivate
```

```powershell
# ocr-service
cd services\ocr-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# Note : ocrmypdf s'installe via pip, mais 7z/tesseract/ghostscript
# ne sont PAS requis pour les tests (subprocess mocké)
pytest -q
deactivate
```

```powershell
# orchestrator
cd services\orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
deactivate
```

### Linux / macOS (bash)

```bash
# prep-service
cd services/prep-service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
deactivate
```

```bash
# ocr-service
cd services/ocr-service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
deactivate
```

```bash
# orchestrator
cd services/orchestrator
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
deactivate
```

---

## Setup JDK 21 + Maven 3.9+

### Vérifications

```powershell
# Windows PowerShell
java --version
# Attendu : openjdk 21.x.x ...

mvn --version
# Attendu : Apache Maven 3.9.x ...
# Java version: 21.x.x
```

```bash
# Linux / macOS
java --version
mvn --version
```

### Build desktop-app

```powershell
# Windows PowerShell
cd desktop-app
mvn -q -DskipTests package
# Résultat : target/desktop-app-0.1.0.jar
```

```bash
# Linux / macOS
cd desktop-app
mvn -q -DskipTests package
```

---

## Lancer l'ensemble avec Docker Compose

```powershell
# Depuis la racine du dépôt
docker compose up -d --build

# Vérifier l'état
docker compose ps

# Suivre les logs
docker compose logs --follow
```

### Ports exposés localement

| Service | Port local | Port interne | Endpoint de vérification |
|---|---|---|---|
| `prep-service` | `18081` | `8080` | `http://localhost:18081/info` |
| `ocr-service` | `18082` | `8080` | `http://localhost:18082/info` |
| `orchestrator` | `18083` | `8080` | `http://localhost:18083/metrics` |

---

## Lancer l'application desktop JavaFX

### Prérequis

1. Stack Docker démarrée : `docker compose up -d --build` (orchestrateur sur **port 18083** côté hôte)
2. Java 21+, Maven 3.9+

---

### Architecture UI desktop (FXML + Controllers)

L'interface est construite via JavaFX FXML (depuis la migration 2026-02-28) :

```
MainApp.start()
  └── FXMLLoader → src/main/resources/fxml/MainView.fxml
        ├── <fx:include> → DuplicatesView.fxml → DuplicatesController
        ├── <fx:include> → JobsView.fxml → JobsController
        └── <fx:include> → ConfigView.fxml → ConfigController

Injection des services (sans ServiceLocator) :
  MainApp crée AppServices.createDefault()
  → MainController.setServices(services)
  → propagé aux 3 sous-controllers via setters
```

**Packages clés :**
- `...service.AppServices` — container DI (OrchestratorClient + DuplicateService + ConfigService)
- `...ui.controller.*` — 4 controllers FXML
- `...util.FxUtils` — helpers UI statiques (openDirectory, showError)

---

### Lancement via IntelliJ (Run/Debug)

#### 1. Import Maven


1. Ouvrir le dossier racine `comic2pdf-app/` dans IntelliJ IDEA
2. IntelliJ détecte automatiquement `desktop-app/pom.xml`
3. Attendre la résolution des dépendances Maven

#### 2. Configuration du JDK

- **File → Project Structure → Project**
  - SDK : Java 21
  - Language level : 21

#### 3. Configurations Run/Debug disponibles

Le dépôt inclut 3 configurations prêtes à l'emploi (dossier `.run/` à la racine) :

| Configuration | Type | Description |
|---|---|---|
| **Comic2PDF - Desktop Debug** | Application | Lancement direct via `MainApp` (support debug complet) |
| **Comic2PDF - Desktop Run (Maven)** | Maven | Lancement via `mvn javafx:run` |
| **Comic2PDF - Desktop UI Tests** | Maven | Exécution des tests UI (`mvn -Pui-tests test`) |

**Variable d'environnement obligatoire** : `ORCHESTRATOR_URL=http://localhost:18083`

> **Important** : `ORCHESTRATOR_URL` est une **variable d'environnement**, pas une propriété système `-D`.
> Les configurations `.run/*.xml` la définissent automatiquement.

#### 4. Lancer l'application

1. Sélectionner `Comic2PDF - Desktop Debug` ou `Comic2PDF - Desktop Run (Maven)` dans le menu déroulant
2. Cliquer sur **Run** (▶) ou **Debug** (🐛)

---

### Lancement via scripts (CLI)

#### Windows PowerShell

```powershell
.\scripts\run_desktop.ps1
```

Le script exporte automatiquement `ORCHESTRATOR_URL=http://localhost:18083` puis lance `mvn javafx:run`.

#### Linux / macOS

```bash
./scripts/run_desktop.sh
```

#### Méthode manuelle (développement)

**Windows PowerShell** :
```powershell
# ORCHESTRATOR_URL doit être une variable d'environnement (pas -D)
$env:ORCHESTRATOR_URL = "http://localhost:18083"
cd desktop-app
mvn -q javafx:run
```

**Linux / macOS** :
```bash
# ORCHESTRATOR_URL doit être une variable d'environnement (pas -D)
export ORCHESTRATOR_URL="http://localhost:18083"
cd desktop-app
mvn -q javafx:run
```

> **Rappel** : `ORCHESTRATOR_URL` est lu via `System.getenv()` dans [OrchestratorClient.java](../desktop-app/src/main/java/com/comic2pdf/desktop/OrchestratorClient.java).
> Utiliser une variable d'environnement, **jamais** une propriété `-D`.

---



### Variables communes (tous les services)

| Variable | Services | Défaut | Description |
|---|---|---|---|
| `DATA_DIR` | prep, ocr, orchestrator | `/data` | Chemin racine du volume partagé Docker |
| `LOG_JSON` | prep, ocr, orchestrator, desktop | `false` | `true` = logs JSON structurés (une ligne JSON par entrée de log) |

### Variables prep-service et ocr-service

| Variable | Services | Défaut | Description |
|---|---|---|---|
| `SERVICE_CONCURRENCY` | prep, ocr | `1` | Nombre de jobs traités en parallèle par ce service |

### Variables orchestrateur

| Variable | Défaut | Description |
|---|---|---|
| `PREP_URL` | `http://prep-service:8080` | URL interne Docker du prep-service |
| `OCR_URL` | `http://ocr-service:8080` | URL interne Docker du ocr-service |
| `POLL_INTERVAL_MS` | `1000` | Intervalle de polling du watch-folder (en millisecondes) |
| `PREP_CONCURRENCY` | `2` | Nombre maximal de jobs PREP soumis en parallèle |
| `OCR_CONCURRENCY` | `1` | Nombre maximal de jobs OCR soumis en parallèle |
| `MAX_JOBS_IN_FLIGHT` | `3` | Nombre maximal de jobs actifs simultanément toutes étapes confondues |
| `MAX_ATTEMPTS_PREP` | `3` | Nombre maximal de tentatives pour l'étape PREP avant ERROR |
| `MAX_ATTEMPTS_OCR` | `3` | Nombre maximal de tentatives pour l'étape OCR avant ERROR |
| `OCR_LANG` | `fra+eng` | Langue(s) OCR Tesseract (tokens triés — `fra+eng` ≡ `eng+fra`) |
| `JOB_TIMEOUT_SECONDS` | `600` | Délai max (en secondes) par étape avant de considérer le job stale |
| `KEEP_WORK_DIR_DAYS` | `7` | Jours de rétention des workdirs. `0` = suppression immédiate après DONE |
| `MIN_PDF_SIZE_BYTES` | `1024` | Taille minimale (octets) du PDF final pour le considérer valide |
| `DISK_FREE_FACTOR` | `2.0` | Espace disque requis = taille_fichier_entrant × facteur |
| `MAX_INPUT_SIZE_MB` | `500` | Taille maximale acceptée pour un fichier entrant (Mo) |
| `ORCHESTRATOR_HTTP_PORT` | `8080` | Port d'écoute du serveur HTTP de l'orchestrateur |
| `ORCHESTRATOR_HTTP_BIND` | `0.0.0.0` | Adresse IP de bind du serveur HTTP |

### Variables desktop-app

| Variable | Défaut | Description |
|---|---|---|
| `ORCHESTRATOR_URL` | `http://localhost:8080` | URL de l'orchestrateur depuis l'application Desktop |

> **Attention** : en mode Docker avec les ports exposés tels que définis dans `docker-compose.yml`, l'URL depuis le Desktop est `http://localhost:18083`.

---

## Setup tools/ (CLI et watch local)

Le package `tools/` dispose de son propre venv et requirements.

### Windows (PowerShell)

```powershell
cd tools
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# Vérifier :
pytest -q ..\tests\tools\
deactivate
```

### Linux / macOS (bash)

```bash
cd tools
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q ../tests/tools/
deactivate
```

### Script dédié

```powershell
.\scripts\test_tools.ps1        # Windows
./scripts/test_tools.sh         # Linux / macOS
```

### Variables d'environnement (mode local)

| Variable | Défaut | Description |
|---|---|---|
| `COMIC2PDF_IN_DIR` | `./data/in` | Dossier d'entrée du watcher |
| `COMIC2PDF_OUT_DIR` | `./data/out` | Dossier de sortie des PDFs |
| `COMIC2PDF_LANG` | `fra+eng` | Langue(s) OCR par défaut |
| `COMIC2PDF_HOLD_DIR` | `./data/hold/duplicates` | Dossier doublons |

Ces variables sont des alternatives aux arguments CLI ; les arguments CLI ont priorité.

---

## Lancer en local sans Docker (limitations)

Il est possible de lancer les services Python en local pour le développement, mais avec des contraintes importantes :

### Limitations connues

| Binaire requis | Usage | Disponibilité |
|---|---|---|
| `7z` | Extraction CBZ/CBR dans prep-service | À installer manuellement |
| `img2pdf` | Conversion images → PDF dans prep-service | Installé via pip |
| `ocrmypdf` | OCR PDF dans ocr-service | Installé via pip |
| `tesseract` | Moteur OCR (appelé par ocrmypdf) | À installer manuellement |
| `ghostscript` | Requis par ocrmypdf | À installer manuellement |

### Lancement manuel (développement uniquement)

```powershell
# Windows PowerShell — prep-service
cd services\prep-service
.\.venv\Scripts\Activate.ps1
$env:DATA_DIR = "N:\workspace-dev\comic2pdf-app\data"
uvicorn app.main:app --port 8081 --reload
```

```powershell
# ocr-service (autre terminal)
cd services\ocr-service
.\.venv\Scripts\Activate.ps1
$env:DATA_DIR = "N:\workspace-dev\comic2pdf-app\data"
uvicorn app.main:app --port 8082 --reload
```

```powershell
# orchestrator (autre terminal)
cd services\orchestrator
.\.venv\Scripts\Activate.ps1
$env:DATA_DIR = "N:\workspace-dev\comic2pdf-app\data"
$env:PREP_URL = "http://localhost:8081"
$env:OCR_URL = "http://localhost:8082"
python app/main.py
```

> Cette procédure est **non supportée officiellement** pour la production. Docker est le seul mode supporté.

---

> **Licences** : les outils système installés dans les conteneurs Docker (Ghostscript AGPL-3.0, 7-Zip/p7zip-full,
> Tesseract Apache-2.0) ont leurs propres licences — voir [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).
> ⚠️ Ghostscript (AGPL-3.0) peut imposer des obligations lors de la redistribution d'un binaire dérivé.

---

## Retour

[← Retour à la documentation développeur](README.md)

