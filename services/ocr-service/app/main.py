import os, subprocess, threading, time, json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.utils import ensure_dir, atomic_write_json, read_json, now_iso

DATA_DIR = os.environ.get("DATA_DIR", "/data")
SERVICE_CONCURRENCY = int(os.environ.get("SERVICE_CONCURRENCY", "1"))

QUEUE_DIR = os.path.join(DATA_DIR, "ocr", "queue")
RUNNING_DIR = os.path.join(DATA_DIR, "ocr", "running")
DONE_DIR = os.path.join(DATA_DIR, "ocr", "done")
ERROR_DIR = os.path.join(DATA_DIR, "ocr", "error")

app = FastAPI(title="ocr-service")

def tool_versions():
    out = {}
    try:
        p = subprocess.run(["ocrmypdf", "--version"], capture_output=True, text=True)
        out["ocrmypdf"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["ocrmypdf"] = "unknown"
    try:
        p = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        out["tesseract"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["tesseract"] = "unknown"
    try:
        p = subprocess.run(["gs", "--version"], capture_output=True, text=True)
        out["ghostscript"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["ghostscript"] = "unknown"
    return out

@app.get("/info")
def info():
    return {"service": "ocr-service", "versions": tool_versions()}

class OcrSubmit(BaseModel):
    jobId: str
    rawPdfPath: str
    workDir: str
    lang: str = "fra+eng"
    rotatePages: bool = True
    deskew: bool = True
    optimize: int = 1

@app.post("/jobs/ocr", status_code=202)
def submit(req: OcrSubmit):
    ensure_dir(QUEUE_DIR); ensure_dir(RUNNING_DIR); ensure_dir(DONE_DIR); ensure_dir(ERROR_DIR)
    job_file = os.path.join(QUEUE_DIR, f"{req.jobId}.json")
    if os.path.exists(job_file) or os.path.exists(os.path.join(RUNNING_DIR, f"{req.jobId}.json")):
        return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}
    atomic_write_json(job_file, req.model_dump() | {"state": "QUEUED", "updatedAt": now_iso()})
    return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}

@app.get("/jobs/{job_id}")
def status(job_id: str):
    for d in [QUEUE_DIR, RUNNING_DIR, DONE_DIR, ERROR_DIR]:
        p = os.path.join(d, f"{job_id}.json")
        data = read_json(p)
        if data:
            return data
    raise HTTPException(status_code=404, detail="job not found")


def requeue_running_on_startup():
    ensure_dir(QUEUE_DIR); ensure_dir(RUNNING_DIR)
    for fn in list(os.listdir(RUNNING_DIR)):
        if not fn.endswith(".json"):
            continue
        src = os.path.join(RUNNING_DIR, fn)
        dst = os.path.join(QUEUE_DIR, fn)
        try:
            os.replace(src, dst)
        except Exception:
            pass

# Requeue any RUNNING jobs after a restart (restart-resilient, recalc policy)
requeue_running_on_startup()


def claim_one():
    ensure_dir(QUEUE_DIR); ensure_dir(RUNNING_DIR)
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
    data = read_json(job_meta_path) or {}
    data.update(patch)
    data["updatedAt"] = now_iso()
    atomic_write_json(job_meta_path, data)

def run_job(job_meta_path: str):
    data = read_json(job_meta_path)
    if not data:
        return
    job_id = data["jobId"]
    work_dir = data["workDir"]
    raw_pdf = data["rawPdfPath"]
    lang = data.get("lang", "fra+eng")
    rotate_pages = bool(data.get("rotatePages", True))
    deskew = bool(data.get("deskew", True))
    optimize = int(data.get("optimize", 1))

    job_dir = os.path.join(work_dir, job_id)
    log_path = os.path.join(job_dir, "ocr.log")
    hb_path = os.path.join(job_dir, "ocr.heartbeat")
    final_tmp = os.path.join(job_dir, "final.tmp.pdf")
    final_pdf = os.path.join(job_dir, "final.pdf")

    ensure_dir(job_dir)
    # Recalc-from-scratch policy: cleanup stage artifacts
    for p in [final_tmp, final_pdf, log_path]:
        try: os.remove(p)
        except FileNotFoundError: pass

    update_state(job_meta_path, {"state": "RUNNING", "message": "ocr running"})
    with open(log_path, "a", encoding="utf-8") as log:
        def heartbeat(msg=""):
            with open(hb_path, "w", encoding="utf-8") as hb:
                hb.write(f"{now_iso()} {msg}\n")

        try:
            heartbeat("start")
            cmd = ["ocrmypdf", "--output-type", "pdf"]
            if rotate_pages:
                cmd.append("--rotate-pages")
            if deskew:
                cmd.append("--deskew")
            if optimize is not None:
                cmd += ["--optimize", str(optimize)]
            if lang:
                cmd += ["-l", lang]
            cmd += [raw_pdf, final_tmp]

            log.write("CMD: " + " ".join(cmd) + "\n")
            p = subprocess.run(cmd, capture_output=True, text=True)
            log.write(p.stdout + "\n" + p.stderr + "\n")
            if p.returncode != 0:
                raise RuntimeError(f"ocrmypdf failed rc={p.returncode}")

            os.replace(final_tmp, final_pdf)
            update_state(job_meta_path, {"state": "DONE", "message": "final.pdf ready", "artifacts": {"finalPdf": final_pdf}})
        except Exception as e:
            update_state(job_meta_path, {"state": "ERROR", "message": str(e), "error": {"type": type(e).__name__, "detail": str(e)}})
            raise

def worker_loop(stop_event: threading.Event):
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

stop_event = threading.Event()
threads = []
for _ in range(max(1, SERVICE_CONCURRENCY)):
    t = threading.Thread(target=worker_loop, args=(stop_event,), daemon=True)
    t.start()
    threads.append(t)

@app.on_event("shutdown")
def shutdown():
    stop_event.set()
