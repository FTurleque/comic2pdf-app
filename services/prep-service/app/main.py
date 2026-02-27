"""
Service FastAPI de préparation (extraction CBZ/CBR + génération raw.pdf).
Pipeline : 7z extract -> list images -> img2pdf -> raw.pdf atomique.
"""
import os
import subprocess
import threading
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core import get_tool_versions, list_and_sort_images, images_to_pdf
from app.utils import ensure_dir, atomic_write_json, read_json, now_iso

DATA_DIR = os.environ.get("DATA_DIR", "/data")
SERVICE_CONCURRENCY = int(os.environ.get("SERVICE_CONCURRENCY", "1"))

QUEUE_DIR = os.path.join(DATA_DIR, "prep", "queue")
RUNNING_DIR = os.path.join(DATA_DIR, "prep", "running")
DONE_DIR = os.path.join(DATA_DIR, "prep", "done")
ERROR_DIR = os.path.join(DATA_DIR, "prep", "error")

app = FastAPI(title="prep-service")


@app.get("/info")
def info():
    """Retourne les métadonnées du service et les versions des outils."""
    return {"service": "prep-service", "versions": get_tool_versions()}


class PrepSubmit(BaseModel):
    """Corps de la requête POST /jobs/prep."""
    jobId: str
    inputPath: str
    workDir: str


@app.post("/jobs/prep", status_code=202)
def submit(req: PrepSubmit):
    """Soumet un job de préparation dans la file d'attente."""
    ensure_dir(QUEUE_DIR)
    ensure_dir(RUNNING_DIR)
    ensure_dir(DONE_DIR)
    ensure_dir(ERROR_DIR)
    job_file = os.path.join(QUEUE_DIR, f"{req.jobId}.json")
    running_file = os.path.join(RUNNING_DIR, f"{req.jobId}.json")
    if os.path.exists(job_file) or os.path.exists(running_file):
        return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}
    atomic_write_json(job_file, {
        "jobId": req.jobId,
        "inputPath": req.inputPath,
        "workDir": req.workDir,
        "state": "QUEUED",
        "updatedAt": now_iso(),
    })
    return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}


@app.get("/jobs/{job_id}")
def status(job_id: str):
    """Retourne l'état courant d'un job de préparation."""
    for d in [QUEUE_DIR, RUNNING_DIR, DONE_DIR, ERROR_DIR]:
        p = os.path.join(d, f"{job_id}.json")
        data = read_json(p)
        if data:
            return data
    raise HTTPException(status_code=404, detail="job not found")


def requeue_running_on_startup():
    """
    Au démarrage, replace les jobs RUNNING dans la file d'attente.
    Politique recalcul complet : aucun artefact existant n'est réutilisé.
    """
    ensure_dir(QUEUE_DIR)
    ensure_dir(RUNNING_DIR)
    for fn in list(os.listdir(RUNNING_DIR)):
        if not fn.endswith(".json"):
            continue
        src = os.path.join(RUNNING_DIR, fn)
        dst = os.path.join(QUEUE_DIR, fn)
        try:
            os.replace(src, dst)
        except Exception:
            pass


def claim_one():
    """
    Réclame atomiquement un job depuis la file d'attente.

    :return: Chemin du fichier de métadonnées dans RUNNING_DIR, ou None.
    """
    ensure_dir(QUEUE_DIR)
    ensure_dir(RUNNING_DIR)
    for fn in os.listdir(QUEUE_DIR):
        if not fn.endswith(".json"):
            continue
        src = os.path.join(QUEUE_DIR, fn)
        dst = os.path.join(RUNNING_DIR, fn)
        try:
            os.replace(src, dst)
            return dst
        except Exception:
            continue
    return None


def update_state(job_meta_path: str, patch: dict):
    """
    Met à jour le fichier de métadonnées d'un job.

    :param job_meta_path: Chemin vers le fichier JSON du job.
    :param patch: Champs à fusionner.
    """
    data = read_json(job_meta_path) or {}
    data.update(patch)
    data["updatedAt"] = now_iso()
    atomic_write_json(job_meta_path, data)


def run_job(job_meta_path: str):
    """
    Exécute un job de préparation : extraction 7z + génération raw.pdf.

    :param job_meta_path: Chemin du fichier de métadonnées (dans RUNNING_DIR).
    :raises RuntimeError: En cas d'échec 7z ou d'absence d'images.
    """
    data = read_json(job_meta_path)
    if not data:
        return
    job_id = data["jobId"]
    work_dir = data["workDir"]
    input_path = data["inputPath"]
    job_dir = os.path.join(work_dir, job_id)
    pages_dir = os.path.join(job_dir, "pages")
    log_path = os.path.join(job_dir, "prep.log")
    hb_path = os.path.join(job_dir, "prep.heartbeat")

    ensure_dir(job_dir)
    import shutil as _sh
    _sh.rmtree(pages_dir, ignore_errors=True)
    ensure_dir(pages_dir)
    raw_tmp = os.path.join(job_dir, "raw.tmp.pdf")
    raw_pdf = os.path.join(job_dir, "raw.pdf")
    for p in [raw_tmp, raw_pdf, log_path]:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass

    update_state(job_meta_path, {"state": "RUNNING", "message": "extracting"})

    def heartbeat(msg: str = ""):
        with open(hb_path, "w", encoding="utf-8") as hb:
            hb.write(f"{now_iso()} {msg}\n")

    with open(log_path, "a", encoding="utf-8") as log:
        try:
            heartbeat("start")
            cmd = ["7z", "x", "-y", f"-o{pages_dir}", input_path]
            log.write("CMD: " + " ".join(cmd) + "\n")
            p = subprocess.run(cmd, capture_output=True, text=True)
            log.write(p.stdout + "\n" + p.stderr + "\n")
            if p.returncode != 0:
                raise RuntimeError(f"7z failed rc={p.returncode}")

            heartbeat("listing_images")
            images = list_and_sort_images(pages_dir)
            if not images:
                raise RuntimeError("no images found after extraction")

            update_state(job_meta_path, {"message": f"building pdf ({len(images)} pages)"})
            heartbeat("img2pdf")
            images_to_pdf(images, raw_tmp)
            os.replace(raw_tmp, raw_pdf)
            update_state(job_meta_path, {
                "state": "DONE",
                "message": "raw.pdf ready",
                "artifacts": {"rawPdf": raw_pdf},
            })
        except Exception as e:
            update_state(job_meta_path, {
                "state": "ERROR",
                "message": str(e),
                "error": {"type": type(e).__name__, "detail": str(e)},
            })
            raise


def worker_loop(stop_event: threading.Event):
    """
    Boucle principale du worker de préparation.

    :param stop_event: Événement de signal d'arrêt.
    """
    while not stop_event.is_set():
        job_meta = claim_one()
        if not job_meta:
            time.sleep(0.5)
            continue
        try:
            run_job(job_meta)
            dst = os.path.join(DONE_DIR, os.path.basename(job_meta))
            os.replace(job_meta, dst)
        except Exception:
            dst = os.path.join(ERROR_DIR, os.path.basename(job_meta))
            os.replace(job_meta, dst)


# ---------------------------------------------------------------------------
# Bootstrap : déclenché uniquement par FastAPI au démarrage (pas à l'import)
# ---------------------------------------------------------------------------

_stop_event = threading.Event()
_worker_threads = []


@app.on_event("startup")
def startup():
    """Démarre les workers au lancement du serveur FastAPI."""
    requeue_running_on_startup()
    for _ in range(max(1, SERVICE_CONCURRENCY)):
        t = threading.Thread(target=worker_loop, args=(_stop_event,), daemon=True)
        t.start()
        _worker_threads.append(t)


@app.on_event("shutdown")
def shutdown():
    """Arrête proprement les workers à l'arrêt du serveur FastAPI."""
    _stop_event.set()
