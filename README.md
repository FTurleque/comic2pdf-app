# Comic2PDF (CBR/CBZ -> PDF searchable)

> 📚 **Documentation complète** : [docs/README.md](docs/README.md)

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

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
| **Doublons** | Vue existante : décisions USE_EXISTING_RESULT / DISCARD / FORCE_REPROCESS |
| **Jobs** | Suivi temps-réel (refresh auto 3s) avec état, étape, tentative. Bouton "Ouvrir out/" |
| **Configuration** | PREP_CONCURRENCY, OCR_CONCURRENCY, timeout, langue OCR. Persistance locale + POST /config |

### URL orchestrateur

Configurable via :
1. Variable d'env `ORCHESTRATOR_URL` (défaut `http://localhost:8080`)
2. Champ "URL orchestrateur" dans l'onglet Configuration (persisté dans `%APPDATA%\comic2pdf\config.json`)

---

## 10) Mode sans Docker (CLI / watch local) — À venir

### Limitation actuelle

Les trois services Python (`prep-service`, `ocr-service`, `orchestrator`) sont conçus pour
tourner dans des conteneurs Docker séparés. L'exécution locale sans Docker nécessite :

- La présence des binaires `7z`, `ocrmypdf`, `tesseract`, `ghostscript` dans le PATH
- La gestion manuelle des ports HTTP inter-services

### Architecture future envisagée

Un package Python unique `comic2pdf` regroupant les trois services :

```
tools/
  cli.py           # comic2pdf input.cbz --lang fra+eng --out /tmp
  watch_local.py   # surveillance dossier + pipeline complet en local
```

```bash
# Utilisation CLI envisagée
python tools/cli.py MonComic.cbz --lang fra+eng --out ./pdfs/

# Watch-folder local
python tools/watch_local.py --in ./data/in --out ./data/out
```

Ce mode est **intentionnellement reporté** à une prochaine itération pour :
- Éviter la complexité des imports croisés entre services
- Garantir la stabilité du pipeline Docker actuel
- Permettre de valider les abstractions nécessaires (fonctions pures partagées)

---

## License

This project is licensed under the **MIT License** — see [`LICENSE`](LICENSE).

Third-party components (Ghostscript, Tesseract, 7-Zip, OCRmyPDF, OpenJFX, etc.)
are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) with their respective licenses.

> ⚠️ **Ghostscript (AGPL-3.0)** may impose source code distribution obligations
> when redistributing a derived binary — see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
> for the full disclaimer and distribution notes.
