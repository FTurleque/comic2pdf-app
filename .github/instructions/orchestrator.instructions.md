---
description: Règles de code, tests et architecture pour l'orchestrateur watch-folder
applyTo: services/orchestrator/**
---

# Instructions — orchestrator

## Rôle
Surveiller `data/in/`, orchestrer le pipeline PREP → OCR, gérer la déduplication (jobKey),
les retries (3 par étape), les heartbeats/timeouts et les métriques basiques.
Processus standalone (`python -m app.main`), pas de serveur HTTP.

## Structure des fichiers

```
services/orchestrator/
├── app/
│   ├── __init__.py
│   ├── core.py      # Fonctions pures : canonical_profile, make_job_key,
│   │                #   is_heartbeat_stale, make_empty_metrics, update_metrics, write_metrics
│   ├── main.py      # process_tick, check_stale_jobs, process_loop (entrée __main__)
│   └── utils.py
├── tests/
│   ├── __init__.py
│   ├── test_core.py         # profil, jobKey, heartbeat, métriques
│   └── test_orchestrator.py # doublons, check_stale_jobs
├── requirements.txt         # requests
└── requirements-dev.txt     # -r requirements.txt + pytest, pytest-cov, pytest-mock
```

## Cycle complet d'un tick — `process_tick(in_flight, index, index_path, profile, config)`

La fonction reçoit **tout** en paramètre (pas de lecture de globals dans les tests) :

```
1. check_duplicate_decisions(index, index_path)   ← appliquer decision.json en attente
2. Découverte (si len(in_flight) < max_jobs_in_flight)
   └─ move_atomic src → _staging/ → sha256_file → make_job_key
      ├─ doublon : write_duplicate_report → continue
      └─ nouveau : move_atomic → _staging → job_dir, update_state(DISCOVERED), in_flight[jk]=...
3. Planification PREP (jusqu'à prep_concurrency jobs)
   └─ DISCOVERED/PREP_RETRY + attemptPrep < max_attempts_prep
      ├─ dépassé → ERROR_PREP, move vers error/, del in_flight[jk]
      └─ submit_prep(jk, input_path) → PREP_RUNNING
4. Polling PREP
   └─ poll_job(prep_url, jk) → DONE → PREP_DONE / ERROR → PREP_RETRY
5. Planification OCR (jusqu'à ocr_concurrency jobs)
   └─ PREP_DONE/OCR_RETRY + attemptOcr < max_attempts_ocr
      ├─ dépassé → ERROR_OCR, del in_flight[jk]
      └─ submit_ocr(jk, raw_pdf) → OCR_RUNNING
6. Polling OCR + finalisation
   └─ poll_job(ocr_url, jk) → DONE → move final_pdf → out/, archive input, del in_flight[jk]
                             → ERROR → OCR_RETRY
7. check_stale_jobs(in_flight, config["job_timeout_s"])
8. write_metrics(metrics, config["index_dir"])
```

## Fonctions pures → `core.py`

### Profil et jobKey
- `canonical_profile(prep_info, ocr_info, ocr_lang) -> dict`
  Normalise la langue : `sorted(set(ocr_lang.split("+")))` → `"+".join(tokens)`.
  Inclut les versions des outils dans `profile["ocr"]["tools"]` et `profile["prep"]["tools"]`.

- `stable_json(obj) -> str`
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.

- `make_job_key(file_hash: str, profile: dict) -> tuple[str, str]`
  Retourne `(profile_hash, job_key)` où `job_key = f"{file_hash}__{profile_hash}"`.
  **Signature exacte** — toujours utiliser le dépacking `profile_hash, job_key = make_job_key(...)`.

### Heartbeat
- `is_heartbeat_stale(hb_path, timeout_s, absent_timeout_s=None) -> bool`
  - Absent + `absent_timeout_s == 0` → `True`.
  - Absent + `absent_timeout_s > 0` → `False`.
  - Présent : `time.time() - os.path.getmtime(hb_path) > timeout_s`.
  - `absent_timeout_s` défaut = `2 * timeout_s`.

### Métriques
- `make_empty_metrics() -> dict` : `{"done": 0, "error": 0, "running": 0, "queued": 0, "updatedAt": ""}`.
- `update_metrics(metrics, event) -> dict` : incrémente si `event` est une clé valide, sinon ignore.
- `write_metrics(metrics, index_dir) -> str` : crée `index_dir` si absent, écrit `metrics.json`, retourne le chemin.

## Fonctions importantes → `main.py`

### Déduplication — `write_duplicate_report(job_key, incoming_path, existing, profile)`
1. Déplacer `incoming_path` vers `hold/duplicates/<jobKey>/<ts>__<nom>`.
2. Écrire `reports/duplicates/<jobKey>.json` :
   ```json
   {
     "jobKey": "...",
     "detectedAt": "...",
     "incoming": {"fileName": "...", "path": "...", "sizeBytes": 0},
     "existing": {...},
     "profile": {...},
     "actions": ["USE_EXISTING_RESULT", "DISCARD", "FORCE_REPROCESS"]
   }
   ```
3. Écrire `hold/duplicates/<jobKey>/status.json` : `{"state": "DUPLICATE_PENDING"}`.

### Décisions — `check_duplicate_decisions(index, index_path)`
- `USE_EXISTING_RESULT` → copier le PDF existant vers `out/` (si non existant), archiver le fichier entrant.
- `DISCARD` → `os.remove()` du fichier entrant.
- `FORCE_REPROCESS` → déplacer vers `in/` avec suffixe `__force-<nonce[:8]>`.
- Nettoyage : supprimer `decision.json`, le rapport JSON et `status.json`.

### Heartbeat-check — `check_stale_jobs(in_flight, timeout_s)`
```python
if stage == "PREP_RUNNING":
    hb_path = os.path.join(WORK_DIR, job_key, "prep.heartbeat")
    if is_heartbeat_stale(hb_path, timeout_s):
        update_state(job_key, {"state": "PREP_TIMEOUT", "message": f"heartbeat stale after {timeout_s}s"})
        meta["stage"] = "PREP_RETRY"
elif stage == "OCR_RUNNING":
    hb_path = os.path.join(WORK_DIR, job_key, "ocr.heartbeat")
    if is_heartbeat_stale(hb_path, timeout_s):
        update_state(job_key, {"state": "OCR_TIMEOUT", ...})
        meta["stage"] = "OCR_RETRY"
```

## Dict `config` passé à `process_tick`

```python
config = {
    "prep_url": str,          # PREP_URL
    "ocr_url": str,           # OCR_URL
    "work_dir": str,          # WORK_DIR
    "max_jobs_in_flight": int,
    "prep_concurrency": int,
    "ocr_concurrency": int,
    "max_attempts_prep": int,
    "max_attempts_ocr": int,
    "job_timeout_s": int,     # JOB_TIMEOUT_SECONDS
    "index_dir": str,         # INDEX_DIR
    "metrics": dict,          # partagé entre les ticks (même référence)
}
```

## États d'un job (`state.json`)

```
DISCOVERED → PREP_SUBMITTED → PREP_RUNNING → PREP_DONE
           → OCR_SUBMITTED  → OCR_RUNNING  → DONE

Erreurs : PREP_ERROR, OCR_ERROR, PREP_TIMEOUT, OCR_TIMEOUT, ERROR
```

## Tests

### Exigences
- `requests.get` / `requests.post` toujours mockés.
- `monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold/duplicates"))` pour les dossiers globaux.
- `tmp_path` (pytest) pour l'isolation filesystem.
- Ne pas appeler `process_loop()` dans les tests — utiliser `process_tick()` ou les fonctions individuelles.

### Cas minimaux — `test_core.py`
- `canonical_profile` : même entrée → même hash. `fra+eng` ≡ `eng+fra`.
- `stable_json` : ordre des clés ne change pas le résultat.
- `make_job_key` : change si `file_hash` change, change si profil change, format `__`.
- `is_heartbeat_stale` : récent → False, vieux → True, absent + timeout 0 → True.
- `update_metrics` : incrémente la bonne clé, événement inconnu → ignoré.
- `write_metrics` : crée `metrics.json`, contient `updatedAt`.

### Cas minimaux — `test_orchestrator.py`
- `write_duplicate_report` : fichier entrant dans `hold/`, rapport dans `reports/`.
- Rapport contient tous les champs requis (`jobKey`, `incoming`, `existing`, `profile`, `actions`).
- `check_stale_jobs` : heartbeat périmé → `PREP_RETRY` / `OCR_RETRY`.
- `check_stale_jobs` : heartbeat récent → stage inchangé.
- `check_stale_jobs` : stage `DISCOVERED` → non affecté.

### Lancer les tests
```powershell
cd services\orchestrator
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

## Anti-patterns

- ❌ Ne jamais appeler `process_loop()` dans les tests — utiliser `process_tick()`.
- ❌ Ne pas utiliser de globals dans les tests — passer `config` + `monkeypatch`.
- ❌ Ne pas appeler de vrais services HTTP dans les tests unitaires.
- ❌ Ne pas supprimer `index["jobs"]` sans décision utilisateur explicite.
- ❌ Ne pas re-soumettre un doublon sans `decision.json`.
- ❌ Ne pas démarrer `process_loop` à l'import du module (le `if __name__ == "__main__":` existe pour ça).

