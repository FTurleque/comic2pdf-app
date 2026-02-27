# Comic2PDF (CBR/CBZ -> PDF searchable)

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

desktop-app/
  src/test/java/
    .../duplicates/
      DuplicateServiceTest.java  # listDuplicates, writeDecision (JUnit 5)
```
