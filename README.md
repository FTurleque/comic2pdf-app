# Comic2PDF (CBR/CBZ -> PDF searchable)

> 📚 **Documentation complète** : [docs/README.md](docs/README.md)

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
[![CI Status](https://github.com/FTurleque/comic2pdf-app/actions/workflows/ci.yml/badge.svg)](https://github.com/FTurleque/comic2pdf-app/actions/workflows/ci.yml)

Objectif : convertir des fichiers `.cbr` / `.cbz` en **PDF avec texte sélectionnable** (OCR) via une chaîne **Docker** fiable.

## 1) Prérequis
- Docker + Docker Compose

## 2) Lancer en mode Docker (watch-folder)
Depuis la racine :
```bash
docker compose up -d --build
```

Arborescence des volumes (créée automatiquement dans `./data`) :
- `data/in` : déposer des `.cbz` / `.cbr`
- `data/out` : récupérer les PDFs
- `data/work` : jobs temporaires
- `data/hold/duplicates` : doublons en attente de décision
- `data/reports/duplicates` : rapports JSON consommés par l'app Desktop
- `data/error` : jobs en erreur (après 3 tentatives par étape)

### Dépôt fiable (anti-fichier-en-cours-de-copie)
Copier en `.part`, puis renommer quand la copie est finie :
```bash
cp "/chemin/MonComic.cbz" "./data/in/MonComic.cbz.part"
mv "./data/in/MonComic.cbz.part" "./data/in/MonComic.cbz"
```

### Concurrence (config)
Modifier les env vars dans `docker-compose.yml` :
- `PREP_CONCURRENCY`
- `OCR_CONCURRENCY`
- `MAX_JOBS_IN_FLIGHT`
- `MAX_ATTEMPTS_PREP=3`
- `MAX_ATTEMPTS_OCR=3`

## 3) App Desktop (JavaFX)
L'app desktop sert de **front** :
- déposer un fichier dans `in` (copie + rename `.part` -> final)
- afficher les doublons (rapport) et écrire une décision

### Build & run
```bash
cd desktop-app
mvn -q -DskipTests package
mvn -q javafx:run
```

> L'app desktop suppose que la stack docker tourne (mode "orchestrateur + services").

## 4) Décisions doublons
La clé de job = `fileHash__profileHash` (SHA-256), où le **profil inclut les versions des outils**.

Si un jobKey existe déjà, l'orchestrateur place le fichier dans :
`data/hold/duplicates/<jobKey>/...` et écrit :
`data/reports/duplicates/<jobKey>.json`

L'app desktop écrit une décision dans :
`data/hold/duplicates/<jobKey>/decision.json`

Décisions supportées :
- `USE_EXISTING_RESULT`
- `DISCARD`
- `FORCE_REPROCESS` (re-traitement forcé avec un nonce)

## 5) Structure
- `services/prep-service` : extraction (7z) + img2pdf -> raw.pdf
- `services/ocr-service`  : ocrmypdf + tesseract -> final.pdf
- `services/orchestrator` : watch-folder, pipeline, gestion doublons, concurrence

## 6) Tests locaux (sans Docker)

### Prérequis
- Python 3.12 installé et disponible dans le PATH (`python --version`)
- pip installé (`pip --version`)
- Maven 3.9+ (`mvn --version`)
- Java 21 (`java --version`)

---

### Setup recommandé : venv par service Python

```powershell
# prep-service
cd services\prep-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
deactivate

# ocr-service
cd ..\ocr-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
deactivate

# orchestrator
cd ..\orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
deactivate
```

> **Note** : `ocr-service` requiert le paquet `ocrmypdf` comme dépendance prod.
> Sur Windows, `ocrmypdf` s'installe via pip mais les binaires (tesseract, ghostscript)
> **ne sont pas requis** pour les tests unitaires (subprocess entièrement mocké).

---

### Tests Java (desktop-app)

```powershell
cd desktop-app
mvn test
```

Les tests JUnit 5 dans `src/test/java/` sont découverts automatiquement
par maven-surefire-plugin 3.x. Aucune instance JavaFX n'est démarrée.

---

### Script global `run_tests.ps1`

Lance **tous** les tests Python + Java en une seule commande depuis la racine :

```powershell
cd N:\workspace-dev\comic2pdf-app
.\run_tests.ps1
```

Le script :
1. Installe les dépendances dev de chaque service (`pip install -r requirements-dev.txt`)
2. Lance `pytest -q` dans chaque service Python
3. Lance `mvn -q test` dans `desktop-app`
4. Affiche un résumé coloré (PASS/FAIL par lot)
5. Retourne `exit 1` si au moins un lot échoue

> Le script utilise l'environnement Python courant. Pour l'isolation complète,
> activer le venv de chaque service avant de lancer le script,
> ou lancer les services individuellement comme indiqué ci-dessus.

---

### Structure des tests

```
services/
  prep-service/
    requirements.txt          # dépendances prod
    requirements-dev.txt      # + pytest, pillow (smoke test PDF)
    tests/
      test_core.py            # tri naturel, filtrage images, images_to_pdf
  ocr-service/
    requirements-dev.txt
    tests/
      test_core.py            # get_tool_versions, build_ocrmypdf_cmd, requeue
      test_jobs.py            # run_job OK/ERROR (subprocess mocké)
  orchestrator/
    requirements-dev.txt
    tests/
      test_core.py            # canonical_profile, make_job_key, heartbeat, métriques
      test_orchestrator.py    # doublons, check_stale_jobs
      test_robustness.py      # validate_pdf, disk_space, signatures ZIP/RAR, cleanup
      test_http_server.py     # /metrics /jobs /jobs/{key} /config (port éphémère)
      test_logger.py          # format JSON structuré

desktop-app/
  src/test/java/
    .../config/
      ConfigServiceTest.java     # save/load config.json (JUnit 5 + @TempDir)
    OrchestratorClientTest.java  # parsing JobRow, comportement hors-ligne
    .../duplicates/
      DuplicateServiceTest.java  # listDuplicates, writeDecision (JUnit 5)
```

---

## 7) Observabilité (HTTP orchestrateur)

L'orchestrateur expose une **API HTTP minimale** (stdlib Python `http.server`) sur le port `8080`.

### Variables d'environnement

| Variable | Service | Défaut | Description |
|---|---|---|---|
| `ORCHESTRATOR_HTTP_PORT` | orchestrator | `8080` | Port d'écoute HTTP |
| `ORCHESTRATOR_HTTP_BIND` | orchestrator | `0.0.0.0` | Adresse IP de bind |
| `ORCHESTRATOR_URL`       | desktop-app  | `http://localhost:8080` | URL vers l'orchestrateur |

### Endpoints

```bash
# Métriques (done, error, disk_error, pdf_invalid, input_rejected_*, ...)
curl http://localhost:8080/metrics

# Liste des jobs
curl http://localhost:8080/jobs

# Détail d'un job
curl http://localhost:8080/jobs/<jobKey>

# Configuration courante
curl http://localhost:8080/config

# Modifier la configuration à chaud
curl -X POST http://localhost:8080/config \
  -H "Content-Type: application/json" \
  -d '{"prep_concurrency": 3, "ocr_concurrency": 2, "job_timeout_s": 900}'
```

---

## 8) Robustesse FS + Hardening

### Variables d'environnement supplémentaires

| Variable | Service | Défaut | Description |
|---|---|---|---|
| `KEEP_WORK_DIR_DAYS` | orchestrator | `7` | Jours avant suppression des workdirs. `0` = suppression immédiate après DONE |
| `MIN_PDF_SIZE_BYTES` | orchestrator | `1024` | Taille minimale du PDF final pour le considérer valide |
| `DISK_FREE_FACTOR`   | orchestrator | `2.0` | Espace disque libre requis = taille_entrée × facteur |
| `MAX_INPUT_SIZE_MB`  | orchestrator | `500` | Taille maximale d'un fichier entrant (Mo) |
| `LOG_JSON`           | tous         | `false` | `true` pour logs JSON structurés (une ligne JSON par log) |

### Validations automatiques

1. **Taille fichier** : un fichier trop grand est refusé avant traitement → `data/error/`
2. **Signature ZIP/RAR** : un fichier sans magic bytes valides est refusé → `data/error/`
3. **Espace disque** : vérifié avant démarrage PREP (input_size × DISK_FREE_FACTOR)
4. **PDF final** : validé (header `%PDF-` + taille min) avant move vers `data/out/`
5. **Cleanup workdir** : janitor périodique (toutes les 600s) supprime les workdirs âgés

---

## 9) Desktop JavaFX — Interface améliorée

L'interface est désormais organisée en **3 onglets** :

| Onglet | Fonctionnalité |
|---|---|
| **Doublons** | Décisions USE_EXISTING_RESULT / DISCARD / FORCE_REPROCESS avec détail incoming vs existing |
| **Jobs** | Suivi temps-réel (refresh auto 3s + backoff) avec recherche, filtres état, panneau détail, actions copier/ouvrir |
| **Configuration** | PREP_CONCURRENCY, OCR_CONCURRENCY, timeout, langue OCR, clé API. Persistance locale + POST /config |

### URL orchestrateur

Configurable via :
1. Variable d'env `ORCHESTRATOR_URL` (défaut `http://localhost:8080`)
2. Champ "URL orchestrateur" dans l'onglet Configuration (persisté dans le fichier config utilisateur)

---

## 10) Sécurité

### Authentification `POST /config`

L'endpoint `POST /config` de l'orchestrateur est protégé par un token API.

**Règle de comportement :**
- `ORCHESTRATOR_API_KEY` définie → header `X-Api-Key` requis sur `POST /config` (comparaison constant-time)
  - Mauvaise clé ou header absent → `401 Unauthorized`
- `ORCHESTRATOR_API_KEY` non définie → `POST /config` accepté uniquement depuis `127.0.0.1` / `::1`
  - Autre IP → `403 Forbidden`
- `GET /jobs`, `GET /config`, `GET /metrics` restent **sans authentification** (lecture seule)

**Configuration :**

```bash
# Docker Compose — ajouter dans la section environment de l'orchestrateur
ORCHESTRATOR_API_KEY=votre-cle-secrete-longue
```

```powershell
# Desktop — Variable d'environnement (prioritaire)
$env:ORCHESTRATOR_API_KEY = "votre-cle-secrete-longue"
mvn javafx:run
```

Ou via l'onglet **Configuration** de l'app desktop (champ "Clé API", masqué).

### Stockage de la clé API côté desktop

Priorité de résolution (option A > option B) :

| Priorité | Source | Notes |
|---|---|---|
| **A** | Env var `ORCHESTRATOR_API_KEY` | Toujours prioritaire. Champ UI désactivé si active. |
| **B** | Champ "Clé API" dans l'onglet Config | Persisté dans le fichier config utilisateur ci-dessous. |

**Emplacement du fichier config utilisateur :**

| OS | Chemin |
|---|---|
| Windows | `%APPDATA%\comic2pdf\config.json` |
| Linux/macOS | `${XDG_CONFIG_HOME:-~/.config}/comic2pdf/config.json` |

Sur Unix, le fichier est créé avec les permissions `600` (rw-------) automatiquement.
Sur Windows, la sécurité repose sur les ACL du dossier `%APPDATA%` (restreint à l'utilisateur courant).

> **Important** : ne jamais committer ce fichier (`config.json` est ignoré par `.gitignore`).

### Protection Zip-Slip (prep-service)

Après extraction via 7z, tous les chemins d'images sont vérifiés via `realpath` pour
s'assurer qu'ils restent sous le dossier `pages/`. Toute tentative de zip-slip provoque :
- Suppression du workdir entier
- Job mis en état `ERROR` avec message explicite
- Aucun `raw.pdf` produit

---

## 11) CI GitHub Actions

### Workflow principal (`ci.yml`)

Déclenché sur `push` et `pull_request` vers `main` :

| Job | Description |
|---|---|
| `python-tests` | pytest + couverture (coverage.xml) pour chaque service Python |
| `python-audit` | pip-audit sur les dépendances de production |
| `java-tests` | mvn test + rapport JaCoCo |
| `java-audit` | OWASP Dependency-Check (sur `main` uniquement ou label `run-audit`) |

### Workflow E2E (`e2e.yml`)

Déclenché **uniquement** par :
- `workflow_dispatch` (bouton GitHub Actions)
- Label PR `run-e2e`

Scénario : `docker compose up -d` → déposer un CBZ → attendre PDF dans `data/out/` → vérifier.

**Commandes locales équivalentes :**

```bash
# Linux/macOS
docker compose up -d --build
python tests/e2e/test_pipeline_e2e.py
docker compose down
```

```powershell
# Windows PowerShell
docker compose up -d --build
python tests/e2e/test_pipeline_e2e.py
docker compose down
```

**Variables d'environnement E2E :**

| Variable | Défaut | Description |
|---|---|---|
| `DATA_DIR` | `./data` | Chemin du dossier data/ |
| `E2E_TIMEOUT` | `120` | Timeout en secondes |
| `E2E_POLL_INTERVAL` | `2` | Intervalle de poll en secondes |

---

## 10) Mode sans Docker (CLI / watch local)

### Prérequis

- `7z` (7-Zip) dans le PATH — [7-zip.org](https://www.7-zip.org/) · `apt install p7zip-full` · `brew install p7zip`
- `ocrmypdf`, `tesseract`, `ghostscript` — `pip install ocrmypdf` + binaires système
- `img2pdf` — inclus dans `tools/requirements.txt`

### Installation

```powershell
# Windows PowerShell
cd tools
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux / macOS
cd tools && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Vérification des dépendances

```bash
python tools/cli.py --check-deps
```

### CLI — conversion ponctuelle

```bash
# Conversion CBZ → PDF (avec OCR)
python tools/cli.py MonComic.cbz --lang fra+eng --out ./pdfs/

# Sans OCR (rapide)
python tools/cli.py MonComic.cbz --no-ocr --out ./pdfs/

# Options
python tools/cli.py --help
```

### Watch-folder local

```bash
# Surveiller ./data/in → PDFs dans ./data/out
python tools/watch_local.py --in ./data/in --out ./data/out --lang fra+eng

# Options
python tools/watch_local.py --help
```

La convention `.part` → rename est respectée identiquement au mode Docker.
Les doublons sont détectés et déplacés dans `--hold-dir` (défaut : `./data/hold/duplicates`).

### Architecture

```
tools/
  __init__.py         # Marqueur de package
  pipeline_core.py    # Fonctions pures autonomes (extraction, images, OCR cmd, jobKey)
  deps.py             # Détection dépendances système (shutil.which + messages actionnables)
  cli.py              # Interface CLI (argparse)
  watch_local.py      # Surveillance dossier + pipeline local
  requirements.txt    # img2pdf
  requirements-dev.txt# + pytest, pytest-cov, pytest-mock, pillow

tests/tools/
  test_deps.py        # Tests détection dépendances
  test_pipeline_core.py # Tests fonctions pures
  test_cli.py         # Tests CLI (subprocess mocké)
  test_watch.py       # Tests watcher (subprocess mocké)
  test_cli_e2e.py     # E2E minimal mocké + test réel optionnel (skipif 7z absent)
```

> **Documentation complète** : [`docs/user/usage.md`](docs/user/usage.md) · [`docs/user/installation.md`](docs/user/installation.md)

---

## License

This project is licensed under the **MIT License** — see [`LICENSE`](LICENSE).

Third-party components (Ghostscript, Tesseract, 7-Zip, OCRmyPDF, OpenJFX, etc.)
are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) with their respective licenses.

> ⚠️ **Ghostscript (AGPL-3.0)** may impose source code distribution obligations
> when redistributing a derived binary — see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
> for the full disclaimer and distribution notes.
