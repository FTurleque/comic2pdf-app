# GitHub Copilot — Instructions globales `comic2pdf-app`

## Vue d'ensemble du dépôt

`comic2pdf-app` convertit des archives BD (`.cbz` / `.cbr`) en **PDF avec texte sélectionnable** (OCR).
Trois services Python + une application desktop JavaFX.

```
comic2pdf-app/
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/          # Règles ciblées par zone (prep, ocr, orchestrateur, desktop)
│   ├── agents/                # Agents de maintenance (services-maintainer, desktop-maintainer)
│   └── prompts/               # Prompts de tâches réutilisables (12 fichiers)
├── services/
│   ├── prep-service/          # Extraction CBZ/CBR + raw.pdf (7z + img2pdf)
│   │   ├── app/               # core.py, main.py, utils.py
│   │   ├── tests/             # test_core.py
│   │   ├── requirements.txt
│   │   └── requirements-dev.txt
│   ├── ocr-service/           # OCR raw.pdf → final.pdf (ocrmypdf + Tesseract)
│   │   ├── app/               # core.py, main.py, utils.py
│   │   ├── tests/             # test_core.py, test_jobs.py
│   │   ├── requirements.txt
│   │   └── requirements-dev.txt
│   └── orchestrator/          # Watch-folder, pipeline, déduplication, heartbeats, métriques
│       ├── app/               # core.py, main.py, utils.py
│       ├── tests/             # test_core.py, test_orchestrator.py
│       ├── requirements.txt
│       └── requirements-dev.txt
├── desktop-app/               # Interface JavaFX : dépôt fichiers + gestion doublons
│   └── src/main/java/com/comic2pdf/desktop/
│       ├── MainApp.java
│       ├── MainView.java
│       ├── DupRow.java
│       └── duplicates/
│           ├── DuplicateService.java
│           └── DuplicateDecision.java
├── data/                      # Volume partagé
│   ├── in/                    # Fichiers entrants .cbz/.cbr (ignorer .part)
│   ├── out/                   # PDF finaux *__job-<jobKey>.pdf
│   ├── work/                  # Dossiers de travail par jobKey
│   ├── archive/               # Fichiers sources traités avec succès
│   ├── error/                 # Fichiers en erreur (MAX_ATTEMPTS dépassé)
│   ├── hold/duplicates/       # Doublons en attente de décision
│   ├── reports/duplicates/    # Rapports JSON des doublons
│   └── index/                 # jobs.json + metrics.json
├── docker-compose.yml
├── run_tests.ps1              # Script PowerShell : tous les tests Python + Java
└── README.md
```

---

## Architecture et flux de données

```
data/in/*.cbz|cbr  →  orchestrator  →  prep-service:8080  →  ocr-service:8080  →  data/out/
                        watch-folder       raw.pdf              final.pdf          *__job-<jobKey>.pdf
```

1. Orchestrateur détecte `.cbz`/`.cbr` dans `data/in/` (ignore `.part`).
2. Calcule `jobKey = SHA256(fichier)__SHA256(profil_canonique)`.
3. Doublon (même `jobKey` dans l'index) → `hold/duplicates/<jobKey>/` + `reports/duplicates/<jobKey>.json`.
4. Sinon : PREP → OCR → archivage dans `data/archive/`.
5. Sortie nommée `<nom_original>__job-<jobKey>.pdf`.

---

## Invariants non négociables

### 1. Pas de réseau externe
Les services Python communiquent **uniquement** entre eux via HTTP interne (`PREP_URL`, `OCR_URL`).
Zéro appel Internet. Zéro dépendance cloud.

### 2. Variables d'environnement

| Variable | Service | Défaut |
|---|---|---|
| `DATA_DIR` | tous | `/data` |
| `PREP_URL` | orchestrator | `http://prep-service:8080` |
| `OCR_URL` | orchestrator | `http://ocr-service:8080` |
| `POLL_INTERVAL_MS` | orchestrator | `1000` |
| `PREP_CONCURRENCY` | orchestrator | `2` |
| `OCR_CONCURRENCY` | orchestrator | `1` |
| `MAX_JOBS_IN_FLIGHT` | orchestrator | `3` |
| `MAX_ATTEMPTS_PREP` | orchestrator | `3` |
| `MAX_ATTEMPTS_OCR` | orchestrator | `3` |
| `JOB_TIMEOUT_SECONDS` | orchestrator | `600` |
| `OCR_LANG` | orchestrator | `fra+eng` |
| `SERVICE_CONCURRENCY` | prep, ocr | `1` |

### 3. Trois tentatives par étape — recalcul complet
- Sur retry : **supprimer les artefacts** de l'étape précédente avant de recommencer.
- Dépassement du maximum → état `ERROR`, fichier vers `data/error/`.

### 4. Atomicité des écritures
- Toujours : `*.tmp` → `os.replace()` (rename POSIX/Windows).
- Dépôt entrant : `.part` → `.cbz/.cbr`. Ne jamais lire un `.part`.
- Utiliser `atomic_write_json()` de `app/utils.py` pour tout JSON d'état.

### 5. Déduplication déterministe
- `jobKey = <fileHash>__<profileHash>` — deux SHA-256 séparés par `__`.
- Profil canonique = langues normalisées (tokens triés) + versions des outils.
- `eng+fra` ≡ `fra+eng` → même `profileHash`.
- Décisions : `USE_EXISTING_RESULT` | `DISCARD` | `FORCE_REPROCESS`.
- Aucune re-soumission sans `decision.json` écrit par l'app desktop.

### 6. Heartbeat et timeout
- Workers écrivent `<job_dir>/prep.heartbeat` ou `ocr.heartbeat` à chaque étape clé.
- `check_stale_jobs(in_flight, timeout_s)` bascule les jobs périmés en `*_RETRY`.
- Heartbeat absent → stale après `2 × JOB_TIMEOUT_SECONDS` (évite les faux positifs au démarrage).

### 7. Métriques JSON pur
- Compteurs `done`, `error`, `running`, `queued` via `update_metrics(metrics, event)`.
- Persistés dans `data/index/metrics.json` à chaque tick. Zéro Prometheus.

### 8. Bootstrap non-impactant à l'import
- **prep-service / ocr-service** : threads workers démarrés **uniquement** dans `@app.on_event("startup")` FastAPI (pas à l'import).
  - `prep-service` : `requeue_running_on_startup()` appelé dans le handler startup.
  - `ocr-service` : `requeue_running(RUNNING_DIR, QUEUE_DIR)` (de `core.py`) appelé dans le handler startup.
- **orchestrator** : script pur Python, pas de FastAPI. Démarrage via `if __name__ == "__main__": process_loop()`.
  - `process_tick()` est la fonction pure testable (sans sleep) ; `process_loop()` la boucle infinie.
- Import de n'importe quel module = zéro effet de bord (testabilité garantie).

---

## Règles de contribution Copilot

### Avant d'écrire du code
1. Lire le fichier concerné (`core.py`, `main.py`, `utils.py`).
2. Vérifier les 8 invariants ci-dessus.
3. Décrire les changements (plan) avant de les appliquer.

### Style
- **Patch-only** : changements ciblés, pas de refactoring global non demandé.
- **Ne jamais inventer** de chemins, variables d'env ou formats JSON absents du code.
- **Scope strict** : une modification dans `ocr-service` ne touche pas `prep-service` sans justification documentée.
- **Tests obligatoires** : happy path + ≥ 1 cas d'erreur pour toute logique non triviale.

### Conventions de nommage

| Contexte | Convention | Exemples |
|---|---|---|
| Python fonctions/variables | `snake_case` | `make_job_key`, `job_timeout_s` |
| Python constantes module | `UPPER_CASE` | `MAX_ATTEMPTS_PREP`, `DATA_DIR` |
| Java classes | `PascalCase` | `DuplicateService`, `DupRow` |
| Java méthodes/champs | `camelCase` | `listDuplicates`, `jobKey` |
| JSON clés d'état | `camelCase` | `jobKey`, `updatedAt`, `rawPdf` |
| Fichiers data | `snake_case` | `prep.heartbeat`, `state.json` |

### Tests
- **Python** : `pytest` + `pytest-mock`. `subprocess.run` toujours mocké.
- **Java** : JUnit 5 uniquement. Pas de tests UI JavaFX. `@TempDir` pour l'isolation.
- Aucun outil système requis dans les tests (7z, ocrmypdf, tesseract, ghostscript).

---

## Fichiers de référence

| Fichier | Contenu clé |
|---|---|
| `README.md` | Architecture, Docker, instructions tests locaux |
| `run_tests.ps1` | Script PowerShell racine : tests Python (pytest) + Java (mvn test) |
| `services/prep-service/app/core.py` | `filter_images`, `sort_images`, `list_and_sort_images`, `images_to_pdf`, `get_tool_versions` |
| `services/prep-service/app/main.py` | FastAPI : `/info`, `/jobs/prep`, `/jobs/{id}` — `run_job`, `requeue_running_on_startup` |
| `services/prep-service/app/utils.py` | `ensure_dir`, `atomic_write_json`, `read_json`, `natural_key`, `now_iso` |
| `services/prep-service/tests/test_core.py` | tri naturel, filtrage images, smoke test `images_to_pdf` |
| `services/ocr-service/app/core.py` | `get_tool_versions`, `build_ocrmypdf_cmd`, `requeue_running` |
| `services/ocr-service/app/main.py` | FastAPI : `/info`, `/jobs/ocr`, `/jobs/{id}` — `run_job`, startup `requeue_running` |
| `services/ocr-service/app/utils.py` | `ensure_dir`, `atomic_write_json`, `read_json`, `natural_key`, `now_iso` |
| `services/ocr-service/tests/test_core.py` | `get_tool_versions`, `build_ocrmypdf_cmd`, `requeue_running` (subprocess mocké) |
| `services/ocr-service/tests/test_jobs.py` | `run_job` OK/ERROR (subprocess mocké) |
| `services/orchestrator/app/core.py` | `canonical_profile`, `make_job_key`, `is_heartbeat_stale`, `make_empty_metrics`, `update_metrics`, `write_metrics` |
| `services/orchestrator/app/main.py` | `process_tick`, `process_loop`, `check_stale_jobs`, `write_duplicate_report`, `check_duplicate_decisions` |
| `services/orchestrator/app/utils.py` | `ensure_dir`, `atomic_write_json`, `read_json`, `sha256_file`, `natural_key`, `now_iso` |
| `services/orchestrator/tests/test_core.py` | `canonical_profile`, `make_job_key`, `is_heartbeat_stale`, métriques |
| `services/orchestrator/tests/test_orchestrator.py` | doublons, `check_stale_jobs` (HTTP mocké) |
| `desktop-app/src/main/java/com/comic2pdf/desktop/DupRow.java` | Modèle JavaFX : `jobKey`, `incomingFile`, `existingState` (StringProperty) |
| `desktop-app/src/main/java/com/comic2pdf/desktop/duplicates/DuplicateDecision.java` | Enum : `USE_EXISTING_RESULT`, `DISCARD`, `FORCE_REPROCESS` |
| `desktop-app/src/main/java/com/comic2pdf/desktop/duplicates/DuplicateService.java` | `listDuplicates(dataDir)`, `writeDecision(dataDir, jobKey, decision)` |
| `desktop-app/src/main/java/com/comic2pdf/desktop/MainView.java` | Vue JavaFX : délègue à `DuplicateService`, dépôt `.part` → rename atomique |
| `desktop-app/src/test/java/com/comic2pdf/desktop/duplicates/DuplicateServiceTest.java` | JUnit 5 : `listDuplicates`, `writeDecision` (filesystem via `@TempDir`) |

---

## Notes spécifiques

- **Suffixe PDF** : `<nom_sans_ext>__job-<jobKey>.pdf` — format figé, ne pas modifier.
- **`make_job_key(file_hash, profile)`** retourne `(profile_hash, job_key)` — toujours utiliser ce tuple.
- **`process_tick()`** reçoit tous ses paramètres explicitement (`in_flight`, `index`, `index_path`, `profile`, `config`) — pas de globals dans les tests.
- **`check_duplicate_decisions(index, index_path)`** lit `hold/duplicates/<jobKey>/decision.json` à chaque tick et applique l'action (`USE_EXISTING_RESULT`, `DISCARD`, `FORCE_REPROCESS`).
- **Requeue au boot** : `prep-service` → `requeue_running_on_startup()` dans `main.py` ; `ocr-service` → `requeue_running(RUNNING_DIR, QUEUE_DIR)` depuis `core.py`. Politique recalcul complet (aucun artefact réutilisé).
- **Desktop** : `MainView` délègue à `DuplicateService`. Toute logique filesystem reste dans le service pur.
- **Dépôt desktop** : `MainView.depositFile()` copie en `.part` puis renomme atomiquement (`Files.move` avec `ATOMIC_MOVE`) — ne jamais lire un `.part`.

---

## Tests locaux (sans Docker)

### Prérequis
- Python 3.12 (`python --version`)
- pip (`pip --version`)
- Maven 3.9+ (`mvn --version`)
- Java 21 (`java --version`)

### Par service Python

```powershell
# prep-service
cd services\prep-service
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q

# ocr-service  (ocrmypdf s'installe via pip ; binaires tesseract/gs non requis pour les tests)
cd ..\ocr-service
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q

# orchestrator
cd ..\orchestrator
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
```

### Java (desktop-app)

```powershell
cd desktop-app
mvn test
```

### Script global

```powershell
# Depuis la racine du dépôt
.\run_tests.ps1
```

Le script installe les dépendances dev de chaque service, lance `pytest -q` dans chaque service Python,
puis `mvn -q test` dans `desktop-app`. Affiche un résumé coloré (PASS/FAIL) et retourne `exit 1` si un lot échoue.

---

## Configuration IA (`.github/`)

### Instructions ciblées (`.github/instructions/`)
| Fichier | Zone couverte |
|---|---|
| `prep-service.instructions.md` | `services/prep-service/**` |
| `ocr-service.instructions.md` | `services/ocr-service/**` |
| `orchestrator.instructions.md` | `services/orchestrator/**` |
| `desktop-app.instructions.md` | `desktop-app/**` |

### Agents (`.github/agents/`)
| Agent | Rôle |
|---|---|
| `services-maintainer.agent.md` | Maintenance des 3 services Python (prep, ocr, orchestrator) |
| `desktop-maintainer.agent.md` | Maintenance de l'application JavaFX |

### Prompts (`.github/prompts/`)
`add-heartbeat-check` · `add-service` · `cli-and-local-mode` · `desktop-enhancements`
· `functional-improvements` · `new-metric` · `observability` · `packaging-and-ux`
· `robust-fs` · `security-hardening` · `testing-and-benchmarks` · `update-desktop-ui`

