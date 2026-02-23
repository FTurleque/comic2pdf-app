import os, subprocess, threading, queue, time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.utils import ensure_dir, atomic_write_json, read_json, list_images_recursive, natural_key, now_iso
import img2pdf

DATA_DIR = os.environ.get("DATA_DIR", "/data")
SERVICE_CONCURRENCY = int(os.environ.get("SERVICE_CONCURRENCY", "1"))

QUEUE_DIR = os.path.join(DATA_DIR, "prep", "queue")
RUNNING_DIR = os.path.join(DATA_DIR, "prep", "running")
DONE_DIR = os.path.join(DATA_DIR, "prep", "done")
ERROR_DIR = os.path.join(DATA_DIR, "prep", "error")

app = FastAPI(title="prep-service")

def tool_versions():
    # Best-effort: return versions as strings
    out = {}
    try:
        r = subprocess.run(["7z"], capture_output=True, text=True)
        # "7-Zip 23.01 ..."
        first = (r.stdout.splitlines() or r.stderr.splitlines() or [""])[0]
        out["7z"] = first.strip()
    except Exception:
        out["7z"] = "unknown"
    out["img2pdf"] = getattr(img2pdf, "__version__", "unknown")
    return out

@app.get("/info")
def info():
    return {"service": "prep-service", "versions": tool_versions()}

class PrepSubmit(BaseModel):
    jobId: str
    inputPath: str
    workDir: str

@app.post("/jobs/prep", status_code=202)
def submit(req: PrepSubmit):
    ensure_dir(QUEUE_DIR); ensure_dir(RUNNING_DIR); ensure_dir(DONE_DIR); ensure_dir(ERROR_DIR)
    job_file = os.path.join(QUEUE_DIR, f"{req.jobId}.json")
    if os.path.exists(job_file) or os.path.exists(os.path.join(RUNNING_DIR, f"{req.jobId}.json")):
        return {"jobId": req.jobId, "statusUrl": f"/jobs/{req.jobId}"}
    atomic_write_json(job_file, {"jobId": req.jobId, "inputPath": req.inputPath, "workDir": req.workDir, "state": "QUEUED", "updatedAt": now_iso()})
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
            os.replace(src, dst)  # atomic claim
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
    input_path = data["inputPath"]
    job_dir = os.path.join(work_dir, job_id)
    pages_dir = os.path.join(job_dir, "pages")
    log_path = os.path.join(job_dir, "prep.log")
    hb_path = os.path.join(job_dir, "prep.heartbeat")

    ensure_dir(job_dir)
    # Recalc-from-scratch policy: cleanup stage artifacts
    if os.path.exists(pages_dir):
        try: subprocess.run(["rm","-rf", pages_dir], check=False)
        except Exception: pass
        import shutil as _sh
        _sh.rmtree(pages_dir, ignore_errors=True)
    ensure_dir(pages_dir)
    raw_tmp = os.path.join(job_dir, "raw.tmp.pdf")
    raw_pdf = os.path.join(job_dir, "raw.pdf")
    for p in [raw_tmp, raw_pdf, log_path]:
        try: os.remove(p)
        except FileNotFoundError: pass

    update_state(job_meta_path, {"state": "RUNNING", "message": "extracting"})
    with open(log_path, "a", encoding="utf-8") as log:
        def heartbeat(msg=""):
            with open(hb_path, "w", encoding="utf-8") as hb:
                hb.write(f"{now_iso()} {msg}\n")

        heartbeat("start")
        # Extract with 7z (works for both CBZ/CBR)
        try:
            cmd = ["7z", "x", "-y", f"-o{pages_dir}", input_path]
            log.write("CMD: " + " ".join(cmd) + "\n")
            p = subprocess.run(cmd, capture_output=True, text=True)
            log.write(p.stdout + "\n" + p.stderr + "\n")
            if p.returncode != 0:
                raise RuntimeError(f"7z failed rc={p.returncode}")

            heartbeat("listing_images")
            images = list_images_recursive(pages_dir)
            if not images:
                raise RuntimeError("no images found after extraction")

            update_state(job_meta_path, {"message": f"building pdf ({len(images)} pages)"})
            heartbeat("img2pdf")
            with open(raw_tmp, "wb") as f:
                f.write(img2pdf.convert(images))

            os.replace(raw_tmp, raw_pdf)  # atomic publish
            update_state(job_meta_path, {"state": "DONE", "message": "raw.pdf ready", "artifacts": {"rawPdf": raw_pdf}})
        except Exception as e:
            update_state(job_meta_path, {"state": "ERROR", "message": str(e), "error": {"type": type(e).__name__, "detail": str(e)}})
            raise

def worker_loop(stop_event: threading.Event):
    while not stop_event.is_set():
        job_meta = claim_one()
        if not job_meta:
            time.sleep(0.5)
            continue
        # run and move meta file to done/error
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
