---
description: Créer un nouveau micro-service Python dans services/ et l'intégrer dans le pipeline
---

# Prompt — add-service

## Goal
Ajouter un nouveau service HTTP asynchrone dans `services/` qui s'intègre dans le pipeline
`comic2pdf-app` entre ou après les services existants.

## Context

Pipeline actuel :
```
orchestrator  →  prep-service:8080  →  ocr-service:8080
```

Chaque service expose :
- `GET /info` → versions du service et des outils.
- `POST /jobs/<service>` (202) → soumettre un job.
- `GET /jobs/{job_id}` → état courant.

L'orchestrateur soumet les jobs, poll l'état et gère les retries/heartbeats.

## Task
Créer `services/<nom>-service/` respectant l'architecture existante.

## Steps

### 1. Créer la structure de dossiers
```
services/<nom>-service/
├── app/
│   ├── __init__.py      # vide
│   ├── core.py          # Fonctions pures testables
│   ├── main.py          # FastAPI app + workers
│   └── utils.py         # Copier depuis services/prep-service/app/utils.py (identique)
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

### 2. Définir `requirements.txt`
```
fastapi
uvicorn[standard]
<outil_principal>
```

### 3. Implémenter `core.py`
```python
"""Module core du <nom>-service. Fonctions pures testables sans serveur."""
import os, subprocess
from typing import List

def get_tool_versions() -> dict:
    """Versions des outils. Retourne 'unknown' si outil absent."""
    out = {}
    try:
        p = subprocess.run(["<outil>", "--version"], capture_output=True, text=True)
        out["<outil>"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["<outil>"] = "unknown"
    return out

def requeue_running(running_dir: str, queue_dir: str) -> int:
    """Déplace les .json de running/ vers queue/ au démarrage."""
    from app.utils import ensure_dir
    ensure_dir(queue_dir); ensure_dir(running_dir)
    count = 0
    for fn in list(os.listdir(running_dir)):
        if not fn.endswith(".json"): continue
        try:
            os.replace(os.path.join(running_dir, fn), os.path.join(queue_dir, fn))
            count += 1
        except Exception: pass
    return count
```

### 4. Implémenter `main.py` (pattern exact à suivre)
```python
"""Service FastAPI <nom>."""
import os, subprocess, threading, time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.core import get_tool_versions, requeue_running
from app.utils import ensure_dir, atomic_write_json, read_json, now_iso

DATA_DIR = os.environ.get("DATA_DIR", "/data")
SERVICE_CONCURRENCY = int(os.environ.get("SERVICE_CONCURRENCY", "1"))

QUEUE_DIR   = os.path.join(DATA_DIR, "<nom>", "queue")
RUNNING_DIR = os.path.join(DATA_DIR, "<nom>", "running")
DONE_DIR    = os.path.join(DATA_DIR, "<nom>", "done")
ERROR_DIR   = os.path.join(DATA_DIR, "<nom>", "error")

app = FastAPI(title="<nom>-service")

@app.get("/info")
def info():
    return {"service": "<nom>-service", "versions": get_tool_versions()}

class <Nom>Submit(BaseModel):
    jobId: str
    <inputField>: str
    workDir: str

@app.post("/jobs/<nom>", status_code=202)
def submit(req: <Nom>Submit):
    ensure_dir(QUEUE_DIR); ensure_dir(RUNNING_DIR); ensure_dir(DONE_DIR); ensure_dir(ERROR_DIR)
    job_file = os.path.join(QUEUE_DIR, f"{req.jobId}.json")
    if os.path.exists(job_file): return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}
    atomic_write_json(job_file, req.model_dump() | {"state": "QUEUED", "updatedAt": now_iso()})
    return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}

@app.get("/jobs/{job_id}")
def status(job_id: str):
    for d in [QUEUE_DIR, RUNNING_DIR, DONE_DIR, ERROR_DIR]:
        data = read_json(os.path.join(d, f"{job_id}.json"))
        if data: return data
    raise HTTPException(status_code=404, detail="job not found")

def run_job(job_meta_path: str):
    """Séquence : cleanup → heartbeat → outil → rename atomique → DONE/ERROR."""
    data = read_json(job_meta_path)
    if not data: return
    job_id   = data["jobId"]
    work_dir = data["workDir"]
    job_dir  = os.path.join(work_dir, job_id)
    hb_path  = os.path.join(job_dir, "<nom>.heartbeat")
    out_tmp  = os.path.join(job_dir, "output.tmp.<ext>")
    out_file = os.path.join(job_dir, "output.<ext>")
    ensure_dir(job_dir)
    # Recalcul complet : nettoyer les artefacts précédents
    for p in [out_tmp, out_file]:
        try: os.remove(p)
        except FileNotFoundError: pass
    # État RUNNING
    data.update({"state": "RUNNING", "message": "<action>"})
    data["updatedAt"] = now_iso()
    atomic_write_json(job_meta_path, data)
    def heartbeat(msg=""):
        with open(hb_path, "w", encoding="utf-8") as hb: hb.write(f"{now_iso()} {msg}\n")
    try:
        heartbeat("start")
        cmd = ["<outil>", ..., out_tmp]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"<outil> failed rc={p.returncode}")
        os.replace(out_tmp, out_file)
        data.update({"state": "DONE", "message": "output ready", "artifacts": {"output": out_file}})
        data["updatedAt"] = now_iso()
        atomic_write_json(job_meta_path, data)
    except Exception as e:
        data.update({"state": "ERROR", "message": str(e),
                     "error": {"type": type(e).__name__, "detail": str(e)}})
        data["updatedAt"] = now_iso()
        atomic_write_json(job_meta_path, data)
        raise

def worker_loop(stop_event: threading.Event):
    while not stop_event.is_set():
        ensure_dir(QUEUE_DIR); ensure_dir(RUNNING_DIR)
        claimed = None
        for fn in os.listdir(QUEUE_DIR):
            if not fn.endswith(".json"): continue
            src = os.path.join(QUEUE_DIR, fn)
            dst = os.path.join(RUNNING_DIR, fn)
            try: os.replace(src, dst); claimed = dst; break
            except Exception: continue
        if not claimed: time.sleep(0.5); continue
        try:
            run_job(claimed)
            os.replace(claimed, os.path.join(DONE_DIR, os.path.basename(claimed)))
        except Exception:
            os.replace(claimed, os.path.join(ERROR_DIR, os.path.basename(claimed)))

_stop_event = threading.Event()

@app.on_event("startup")
def startup():
    requeue_running(RUNNING_DIR, QUEUE_DIR)
    for _ in range(max(1, SERVICE_CONCURRENCY)):
        threading.Thread(target=worker_loop, args=(_stop_event,), daemon=True).start()

@app.on_event("shutdown")
def shutdown():
    _stop_event.set()
```

### 5. Écrire les tests minimaux (`tests/test_core.py`)
```python
from unittest.mock import MagicMock, patch
import pytest, os
from app.core import get_tool_versions, requeue_running

def test_toutes_les_cles_presentes():
    with patch("app.core.subprocess.run", return_value=MagicMock(stdout="<outil> 1.0\n", stderr="")):
        v = get_tool_versions()
    assert "<outil>" in v

def test_outil_absent_retourne_unknown():
    with patch("app.core.subprocess.run", side_effect=FileNotFoundError()):
        v = get_tool_versions()
    assert v["<outil>"] == "unknown"

def test_run_job_ok(tmp_path, mocker):
    # Préparer méta + mock subprocess
    ...
    assert meta["state"] == "DONE"
    assert os.path.exists(os.path.join(job_dir, "output.<ext>"))

def test_run_job_error(tmp_path, mocker):
    mocker.patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="err"))
    with pytest.raises(RuntimeError):
        run_job(meta_path)
    assert read_json(meta_path)["state"] == "ERROR"
```

### 6. Créer le `Dockerfile`
```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends <paquets_systeme> \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn <outil_pip>
WORKDIR /app
COPY app /app/app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 7. Intégrer dans l'orchestrateur

Dans `services/orchestrator/app/main.py` :

```python
# Variables d'environnement
<NOM>_URL          = os.environ.get("<NOM>_URL",          "http://<nom>-service:8080")
<NOM>_CONCURRENCY  = int(os.environ.get("<NOM>_CONCURRENCY",  "1"))
MAX_ATTEMPTS_<NOM> = int(os.environ.get("MAX_ATTEMPTS_<NOM>", "3"))

def submit_<nom>(job_key, input_artifact):
    r = requests.post(<NOM>_URL + "/jobs/<nom>", json={...}, timeout=10)
    if r.status_code not in (200, 202):
        raise RuntimeError(f"<nom> submit failed: {r.status_code}")

# Dans process_tick — Planification <NOM>
# Dans process_tick — Polling <NOM>
# Dans check_stale_jobs — stage "<NOM>_RUNNING"
```

Dans `docker-compose.yml` : ajouter le service et la variable `<NOM>_URL`.

### 8. Valider
```powershell
.\run_tests.ps1
```

## Constraints

- Pas de réseau externe dans le nouveau service.
- `subprocess.run` toujours mocké dans les tests.
- Bootstrap uniquement dans `@app.on_event("startup")`.
- Heartbeat écrit dans `data/work/<jobKey>/<nom>.heartbeat`.
- États : `QUEUED → RUNNING → DONE | ERROR`.
- Rename atomique obligatoire : `output.tmp.<ext>` → `output.<ext>`.
- `requirements-dev.txt` doit inclure `-r requirements.txt`.

