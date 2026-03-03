# Services Python — Tests et Architecture

Services Docker (prep/ocr/orchestrator). Voir README.md à la racine pour l'architecture globale.

---

## Tests unitaires et intégration API

Chaque service Python (`prep-service`, `ocr-service`, `orchestrator`) contient :
- **Tests unitaires** (`tests/test_core.py`) : fonctions pures, aucun outil externe
- **Tests API** (`tests/test_api.py`) : endpoints FastAPI via `TestClient` (**prep et ocr uniquement**)

> **Note** : L'orchestrator n'est pas une application FastAPI (script pur Python).  
> Il n'a donc **pas de tests API**, uniquement des tests unitaires sur la logique pipeline.

---

## Exécution des tests

### Par service (prep-service / ocr-service)

```powershell
cd services\prep-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Tous les tests (unitaires + API)
pytest -q

# Tests API uniquement
pytest -q tests/test_api.py

# Tests unitaires uniquement
pytest -q tests/test_core.py
```

### Orchestrator (uniquement tests unitaires)

```powershell
cd services\orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
```

### Script global (racine du dépôt)

```powershell
# Depuis N:\workspace-dev\comic2pdf-app\
.\run_tests.ps1
```

Lance tous les tests Python (3 services) + tests Java (desktop-app).

---

## Architecture des tests API

### Isolation complète (DATA_DIR)

Les tests API utilisent une fixture `data_dir` qui :
- Injecte `DATA_DIR` vers un répertoire temporaire (`tmp_path`)
- Force le rechargement du module `app.main` pour capturer la nouvelle valeur
- Évite toute pollution des données réelles (`data/`, `%APPDATA%`, etc.)

### Pas de workers en tests

Les tests API mockent `worker_loop` pour éviter le démarrage de threads :
```python
mocker.patch("app.main.worker_loop", autospec=True)
```

Le `TestClient` exécute les événements `startup`/`shutdown`, mais les workers ne tournent pas.

### Aucun outil externe

`subprocess.run` est automatiquement mocké dans les tests existants (`test_core.py`, `test_jobs.py`).  
Les tests API ne nécessitent **aucun binaire** (7z, ocrmypdf, tesseract, ghostscript).

---

## Couverture

| Service | Tests unitaires | Tests API | Remarque |
|---|---|---|---|
| **prep-service** | ✅ `test_core.py`, `test_security.py` | ✅ `test_api.py` | Endpoints `/info`, `/jobs/prep`, `/jobs/{id}` |
| **ocr-service** | ✅ `test_core.py`, `test_jobs.py` | ✅ `test_api.py` | Endpoints `/info`, `/jobs/ocr`, `/jobs/{id}` |
| **orchestrator** | ✅ `test_core.py`, `test_orchestrator.py` | ❌ N/A | Pas FastAPI, script pur |

---

## Tests API — Cas couverts

### prep-service (`test_api.py`)

**GET /info**
- ✅ 200 : métadonnées service + versions outils

**POST /jobs/prep**
- ✅ 202 : soumission job valide
- ✅ 202 : dédoublonnage (job déjà en queue)
- ✅ 422 : payload invalide (champs manquants)
- ✅ Création fichier `prep/queue/{jobId}.json` avec état QUEUED

**GET /jobs/{id}**
- ✅ 200 : job QUEUED
- ✅ 200 : job DONE (avec artifacts)
- ✅ 200 : job ERROR (avec message erreur)
- ✅ 404 : job inconnu

### ocr-service (`test_api.py`)

**GET /info**
- ✅ 200 : métadonnées service + versions (ocrmypdf, tesseract, ghostscript)

**POST /jobs/ocr**
- ✅ 202 : soumission job valide
- ✅ 202 : validation paramètres (lang, rotatePages, deskew, optimize)
- ✅ 202 : valeurs par défaut appliquées (payload minimal)
- ✅ 202 : dédoublonnage
- ✅ 422 : payload invalide (champs manquants)
- ✅ 422 : type invalide (optimize non-int)

**GET /jobs/{id}**
- ✅ 200 : job QUEUED
- ✅ 200 : job RUNNING
- ✅ 200 : job DONE (avec artifacts)
- ✅ 200 : job ERROR (avec message)
- ✅ 404 : job inconnu

---

## Références

- **TestClient FastAPI** : https://fastapi.tiangolo.com/tutorial/testing/
- **pytest-mock** : https://pytest-mock.readthedocs.io/
- **Instructions Copilot** : `.github/copilot-instructions.md`
