# GitHub Copilot — Instructions globales `comic2pdf-app`

## Vue d'ensemble du dépôt

`comic2pdf-app` convertit des archives BD (`.cbz` / `.cbr`) en **PDF avec texte sélectionnable** (OCR).
Trois services Python + une application desktop JavaFX.

```
comic2pdf-app/
├── services/
│   ├── prep-service/     # Extraction CBZ/CBR + raw.pdf (7z + img2pdf)
│   ├── ocr-service/      # OCR raw.pdf → final.pdf (ocrmypdf + Tesseract)
│   └── orchestrator/     # Watch-folder, pipeline, déduplication, heartbeats, métriques
├── desktop-app/          # Interface JavaFX : dépôt fichiers + gestion doublons
├── data/                 # Volume partagé (in/, out/, work/, hold/, reports/, index/)
├── docker-compose.yml
├── run_tests.ps1         # Script PowerShell : tous les tests Python + Java
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
- Threads workers démarrés **uniquement** dans `@app.on_event("startup")` FastAPI.
- `requeue_running_on_startup()` appelé dans ce même handler.
- Import du module seul = zéro effet de bord (testabilité garantie).

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
| `services/prep-service/app/core.py` | `filter_images`, `sort_images`, `images_to_pdf`, `get_tool_versions` |
| `services/ocr-service/app/core.py` | `get_tool_versions`, `build_ocrmypdf_cmd`, `requeue_running` |
| `services/orchestrator/app/core.py` | `canonical_profile`, `make_job_key`, `is_heartbeat_stale`, métriques |
| `services/orchestrator/app/main.py` | `process_tick`, `check_stale_jobs`, `write_duplicate_report` |
| `desktop-app/src/.../duplicates/DuplicateService.java` | `listDuplicates`, `writeDecision` |

---

## Notes spécifiques

- **Suffixe PDF** : `<nom_sans_ext>__job-<jobKey>.pdf` — format figé, ne pas modifier.
- **`make_job_key(file_hash, profile)`** retourne `(profile_hash, job_key)` — toujours utiliser ce tuple.
- **`process_tick()`** reçoit tous ses paramètres explicitement (`in_flight`, `index`, `index_path`, `profile`, `config`) — pas de globals dans les tests.
- **Desktop** : `MainView` délègue à `DuplicateService`. Toute logique filesystem reste dans le service pur.

