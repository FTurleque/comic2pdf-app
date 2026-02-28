---
description: Ajouter ou renforcer la détection de heartbeats périmés dans l'orchestrateur
---

# Prompt — add-heartbeat-check

## Goal
Ajouter ou renforcer la détection des heartbeats périmés dans l'orchestrateur pour un stage donné,
afin de débloquer automatiquement les jobs bloqués sans intervention manuelle.

## Context

- **Heartbeat** : fichier texte écrit par le worker dans `data/work/<jobKey>/<stage>.heartbeat`.
- **Fichiers existants** :
  - `services/orchestrator/app/core.py` → `is_heartbeat_stale(hb_path, timeout_s, absent_timeout_s)`
  - `services/orchestrator/app/main.py` → `check_stale_jobs(in_flight, timeout_s)`, `process_tick`
  - `services/orchestrator/tests/test_orchestrator.py` → `TestCheckStaleJobs`
- **Variable** : `JOB_TIMEOUT_SECONDS` (env, défaut 600s).
- **Stages actuellement surveillés** : `PREP_RUNNING` → `prep.heartbeat`, `OCR_RUNNING` → `ocr.heartbeat`.

## Task
Vérifier que le mécanisme de heartbeat est correctement branché pour **tous les stages `*_RUNNING`**
du pipeline, puis ajouter les tests manquants.

## Steps

### 1. Lire le code existant
```
read_file services/orchestrator/app/core.py       # is_heartbeat_stale
read_file services/orchestrator/app/main.py       # check_stale_jobs (chercher "PREP_RUNNING")
read_file services/orchestrator/tests/test_orchestrator.py  # TestCheckStaleJobs
```

### 2. Identifier les stages non couverts
Dans `check_stale_jobs`, vérifier que chaque stage `<STAGE>_RUNNING` est traité.
Pattern actuel :
```python
if stage == "PREP_RUNNING":
    hb_path = os.path.join(WORK_DIR, job_key, "prep.heartbeat")
    if is_heartbeat_stale(hb_path, timeout_s):
        update_state(job_key, {"state": "PREP_TIMEOUT", "message": f"heartbeat stale after {timeout_s}s"})
        meta["stage"] = "PREP_RETRY"
elif stage == "OCR_RUNNING":
    hb_path = os.path.join(WORK_DIR, job_key, "ocr.heartbeat")
    if is_heartbeat_stale(hb_path, timeout_s):
        update_state(job_key, {"state": "OCR_TIMEOUT", "message": f"heartbeat stale after {timeout_s}s"})
        meta["stage"] = "OCR_RETRY"
```

### 3. Ajouter un stage manquant (si applicable)
Pour un nouveau stage `<NOM>_RUNNING` :
```python
elif stage == "<NOM>_RUNNING":
    hb_path = os.path.join(WORK_DIR, job_key, "<nom>.heartbeat")
    if is_heartbeat_stale(hb_path, timeout_s):
        update_state(job_key, {
            "state": "<NOM>_TIMEOUT",
            "message": f"heartbeat stale after {timeout_s}s",
        })
        meta["stage"] = "<NOM>_RETRY"
```

### 4. Vérifier le worker correspondant
Dans `services/<nom>-service/app/main.py`, s'assurer que `run_job` écrit le heartbeat :
```python
def heartbeat(msg: str = ""):
    with open(hb_path, "w", encoding="utf-8") as hb:
        hb.write(f"{now_iso()} {msg}\n")

heartbeat("start")   # ← au début de run_job
```

### 5. Écrire les tests manquants
Dans `services/orchestrator/tests/test_orchestrator.py`, classe `TestCheckStaleJobs` :

```python
def test_<nom>_running_avec_heartbeat_vieux_bascule_en_retry(self, tmp_path, monkeypatch):
    """Un job <NOM>_RUNNING avec un heartbeat périmé bascule en <NOM>_RETRY."""
    import app.main as orch
    monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

    job_key = "testjob_<nom>"
    job_dir = tmp_path / "work" / job_key
    job_dir.mkdir(parents=True)

    # Heartbeat périmé (700 secondes)
    hb_path = job_dir / "<nom>.heartbeat"
    hb_path.write_text("old\n")
    old_time = time.time() - 700
    os.utime(str(hb_path), (old_time, old_time))

    # state.json pour update_state
    (job_dir / "state.json").write_text(json.dumps({"jobKey": job_key}))

    in_flight = {job_key: {"stage": "<NOM>_RUNNING", "attemptPrep": 0, "attemptOcr": 0}}
    orch.check_stale_jobs(in_flight, timeout_s=600)
    assert in_flight[job_key]["stage"] == "<NOM>_RETRY"

def test_<nom>_running_avec_heartbeat_recent_reste_running(self, tmp_path, monkeypatch):
    """Un job <NOM>_RUNNING avec un heartbeat récent reste en <NOM>_RUNNING."""
    import app.main as orch
    monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

    job_key = "freshjob_<nom>"
    job_dir = tmp_path / "work" / job_key
    job_dir.mkdir(parents=True)

    hb_path = job_dir / "<nom>.heartbeat"
    hb_path.write_text("recent\n")
    os.utime(str(hb_path), None)  # mtime = maintenant
    (job_dir / "state.json").write_text(json.dumps({"jobKey": job_key}))

    in_flight = {job_key: {"stage": "<NOM>_RUNNING", "attemptPrep": 0, "attemptOcr": 0}}
    orch.check_stale_jobs(in_flight, timeout_s=600)
    assert in_flight[job_key]["stage"] == "<NOM>_RUNNING"
```

### 6. Valider
```powershell
cd services\orchestrator
.\.venv\Scripts\python -m pytest -q
```

## Constraints

- Ne pas modifier `is_heartbeat_stale` — elle est correcte et testée.
- `absent_timeout_s=0` est réservé aux tests forçant le stale immédiat.
- Ne pas réduire `JOB_TIMEOUT_SECONDS` sous 60 en production.
- Le format du fichier heartbeat est libre (texte) — ne pas le parser, seulement lire la mtime.
- Un heartbeat absent est stale après `2 × JOB_TIMEOUT_SECONDS` (pas immédiatement).

## Examples

Heartbeat périmé dans les tests :
```python
old_time = time.time() - 700   # > JOB_TIMEOUT_SECONDS=600
os.utime(str(hb_path), (old_time, old_time))
```

Heartbeat récent dans les tests :
```python
os.utime(str(hb_path), None)   # mtime = maintenant
```

Heartbeat forcé stale (absent) :
```python
# Ne pas créer le fichier + passer absent_timeout_s=0 à is_heartbeat_stale
assert is_heartbeat_stale("/absent/path", timeout_s=60, absent_timeout_s=0) is True
```

