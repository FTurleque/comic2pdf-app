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

## Tableau complet des variables d'environnement

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

## Retour

[← Retour à la documentation développeur](README.md)

