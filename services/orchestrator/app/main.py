import os, time, json, shutil, requests, hashlib
from app.utils import ensure_dir, atomic_write_json, read_json, sha256_file, now_iso

DATA_DIR = os.environ.get("DATA_DIR", "/data")
IN_DIR = os.path.join(DATA_DIR, "in")
OUT_DIR = os.path.join(DATA_DIR, "out")
WORK_DIR = os.path.join(DATA_DIR, "work")
ERROR_DIR = os.path.join(DATA_DIR, "error")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
HOLD_DUP_DIR = os.path.join(DATA_DIR, "hold", "duplicates")
DUP_REPORTS_DIR = os.path.join(DATA_DIR, "reports", "duplicates")
INDEX_DIR = os.path.join(DATA_DIR, "index")

PREP_URL = os.environ.get("PREP_URL", "http://prep-service:8080")
OCR_URL = os.environ.get("OCR_URL", "http://ocr-service:8080")

POLL_INTERVAL_MS = int(os.environ.get("POLL_INTERVAL_MS", "1000"))
PREP_CONCURRENCY = int(os.environ.get("PREP_CONCURRENCY", "2"))
OCR_CONCURRENCY = int(os.environ.get("OCR_CONCURRENCY", "1"))
MAX_JOBS_IN_FLIGHT = int(os.environ.get("MAX_JOBS_IN_FLIGHT", "3"))
MAX_ATTEMPTS_PREP = int(os.environ.get("MAX_ATTEMPTS_PREP", "3"))
MAX_ATTEMPTS_OCR = int(os.environ.get("MAX_ATTEMPTS_OCR", "3"))
OCR_LANG = os.environ.get("OCR_LANG", "fra+eng")

def canonical_profile(prep_info: dict, ocr_info: dict) -> dict:
    # Profile includes tool versions (as requested)
    return {
        "ocr": {
            "lang": OCR_LANG,
            "rotatePages": True,
            "deskew": True,
            "optimize": 1,
            "tools": ocr_info.get("versions", {})
        },
        "prep": {
            "tools": prep_info.get("versions", {})
        }
    }

def stable_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_index():
    ensure_dir(INDEX_DIR)
    p = os.path.join(INDEX_DIR, "jobs.json")
    return (read_json(p) or {"jobs": {}}), p

def save_index(index, path):
    atomic_write_json(path, index)

def ensure_layout():
    for d in [IN_DIR, OUT_DIR, WORK_DIR, ERROR_DIR, ARCHIVE_DIR, HOLD_DUP_DIR, DUP_REPORTS_DIR, INDEX_DIR]:
        ensure_dir(d)

def get_service_info(url: str) -> dict:
    try:
        return requests.get(url + "/info", timeout=5).json()
    except Exception:
        return {"service": url, "versions": {"unknown": "unknown"}}

def move_atomic(src: str, dst: str):
    ensure_dir(os.path.dirname(dst))
    os.replace(src, dst)

def base_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]

def job_dir(job_key: str) -> str:
    return os.path.join(WORK_DIR, job_key)

def job_state_path(job_key: str) -> str:
    return os.path.join(job_dir(job_key), "state.json")

def update_state(job_key: str, patch: dict):
    p = job_state_path(job_key)
    data = read_json(p) or {"jobKey": job_key}
    data.update(patch)
    data["updatedAt"] = now_iso()
    atomic_write_json(p, data)

def discover_inputs():
    # Only final .cbz/.cbr (ignore .part)
    for fn in os.listdir(IN_DIR):
        lfn = fn.lower()
        if not (lfn.endswith(".cbz") or lfn.endswith(".cbr")):
            continue
        src = os.path.join(IN_DIR, fn)

        # Claim by moving into a temp staging (pre-hash) to avoid double processing
        # We'll compute hashes in place.
        yield src

def make_job_key(input_path: str, profile: dict) -> tuple[str, str, str]:
    file_hash = sha256_file(input_path)
    profile_hash = sha256_str(stable_json(profile))
    job_key = f"{file_hash}__{profile_hash}"
    return file_hash, profile_hash, job_key

def write_duplicate_report(job_key: str, incoming_path: str, existing: dict, profile: dict):
    ensure_dir(os.path.join(HOLD_DUP_DIR, job_key))
    ensure_dir(DUP_REPORTS_DIR)

    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    hold_name = f"{ts}__{os.path.basename(incoming_path)}"
    hold_path = os.path.join(HOLD_DUP_DIR, job_key, hold_name)
    move_atomic(incoming_path, hold_path)

    report = {
        "jobKey": job_key,
        "detectedAt": now_iso(),
        "incoming": {
            "fileName": os.path.basename(hold_path),
            "path": hold_path,
            "sizeBytes": os.path.getsize(hold_path)
        },
        "existing": existing,
        "profile": profile,
        "actions": ["USE_EXISTING_RESULT", "DISCARD", "FORCE_REPROCESS"]
    }
    atomic_write_json(os.path.join(DUP_REPORTS_DIR, f"{job_key}.json"), report)
    # state for duplicates
    atomic_write_json(os.path.join(HOLD_DUP_DIR, job_key, "status.json"),
                      {"jobKey": job_key, "state": "DUPLICATE_PENDING", "updatedAt": now_iso()})

def check_duplicate_decisions():
    # If desktop writes decision.json, apply it
    for job_key in os.listdir(HOLD_DUP_DIR):
        job_hold = os.path.join(HOLD_DUP_DIR, job_key)
        if not os.path.isdir(job_hold):
            continue
        decision_path = os.path.join(job_hold, "decision.json")
        if not os.path.exists(decision_path):
            continue
        decision = read_json(decision_path) or {}
        action = decision.get("action")
        index, index_path = load_index()
        existing = index["jobs"].get(job_key)
        # Pick the first held file
        held_files = [f for f in os.listdir(job_hold) if f.lower().endswith((".cbz",".cbr"))]
        held_files.sort()
        held_file_path = os.path.join(job_hold, held_files[0]) if held_files else None

        if action == "USE_EXISTING_RESULT" and existing and existing.get("outPdf"):
            # Reuse existing PDF result; also emit an OUT file matching the held base-name.
            try:
                out_pdf = output_path_for(os.path.basename(held_file_path) if held_file_path else "duplicate.cbz", job_key)
                ensure_dir(OUT_DIR)
                if not os.path.exists(out_pdf):
                    shutil.copy2(existing["outPdf"], out_pdf)
            except Exception:
                pass
            if held_file_path:
                ensure_dir(ARCHIVE_DIR)
                move_atomic(held_file_path, os.path.join(ARCHIVE_DIR, os.path.basename(held_file_path)))
        elif action == "DISCARD":
            if held_file_path:
                os.remove(held_file_path)
        elif action == "FORCE_REPROCESS":
            # Create a new jobKey with nonce to avoid collision
            nonce = decision.get("nonce") or sha256_str(now_iso())
            forced_job_key = job_key + "__" + nonce
            # Move held file back into IN with unique name so it will be discovered
            if held_file_path:
                new_name = base_name(held_file_path) + f"__force-{nonce[:8]}" + os.path.splitext(held_file_path)[1]
                move_atomic(held_file_path, os.path.join(IN_DIR, new_name))
        # Cleanup decision/report/status
        try: os.remove(decision_path)
        except FileNotFoundError: pass
        try: os.remove(os.path.join(DUP_REPORTS_DIR, f"{job_key}.json"))
        except FileNotFoundError: pass
        try: os.remove(os.path.join(job_hold, "status.json"))
        except FileNotFoundError: pass
        # If empty folder, remove
        try:
            if not os.listdir(job_hold):
                os.rmdir(job_hold)
        except Exception:
            pass

def submit_prep(job_key: str, input_path: str):
    r = requests.post(PREP_URL + "/jobs/prep", json={"jobId": job_key, "inputPath": input_path, "workDir": WORK_DIR}, timeout=10)
    if r.status_code not in (200, 202):
        raise RuntimeError(f"prep submit failed: {r.status_code} {r.text}")

def submit_ocr(job_key: str, raw_pdf: str):
    r = requests.post(OCR_URL + "/jobs/ocr", json={"jobId": job_key, "rawPdfPath": raw_pdf, "workDir": WORK_DIR, "lang": OCR_LANG, "rotatePages": True, "deskew": True, "optimize": 1}, timeout=10)
    if r.status_code not in (200, 202):
        raise RuntimeError(f"ocr submit failed: {r.status_code} {r.text}")

def poll_job(url: str, job_key: str) -> dict:
    r = requests.get(url + f"/jobs/{job_key}", timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"job status failed: {r.status_code} {r.text}")
    return r.json()

def output_path_for(input_name: str, job_key: str) -> str:
    return os.path.join(OUT_DIR, f"{base_name(input_name)}__job-{job_key}.pdf")

def process_loop():
    ensure_layout()
    prep_info = get_service_info(PREP_URL)
    ocr_info = get_service_info(OCR_URL)
    profile = canonical_profile(prep_info, ocr_info)

    index, index_path = load_index()

    in_flight = {}  # job_key -> {"stage": "PREP"|"OCR", "inputName":..., "inputPath":..., "attemptPrep":int, "attemptOcr":int}

    while True:
        ensure_layout()
        check_duplicate_decisions()

        # discover new files if capacity
        if len(in_flight) < MAX_JOBS_IN_FLIGHT:
            for src in list(discover_inputs()):
                # Claim by moving into a staging file inside WORK using temporary name, then hash
                # Safer: move directly into a temp job folder based on time, then compute hash
                ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
                original_name = os.path.basename(src)
                staging_dir = os.path.join(WORK_DIR, "_staging", ts + "_" + original_name)
                ensure_dir(os.path.dirname(staging_dir))
                try:
                    move_atomic(src, staging_dir)
                except Exception:
                    continue  # someone else took it

                file_hash, profile_hash, job_key = make_job_key(staging_dir, profile)

                # Duplicate check on job_key
                existing = index["jobs"].get(job_key)
                if existing:
                    write_duplicate_report(job_key, staging_dir, existing, profile)
                    continue

                # Create canonical job folder and move input into it
                jdir = job_dir(job_key)
                ensure_dir(jdir)
                input_path = os.path.join(jdir, original_name)
                move_atomic(staging_dir, input_path)

                # init states
                update_state(job_key, {"state": "DISCOVERED", "profile": profile, "fileHash": file_hash, "profileHash": profile_hash, "input": {"name": os.path.basename(input_path), "path": input_path}})
                index["jobs"][job_key] = {"jobKey": job_key, "state": "DISCOVERED", "inputName": os.path.basename(input_path), "outPdf": None, "updatedAt": now_iso()}
                save_index(index, index_path)

                in_flight[job_key] = {"stage": "DISCOVERED", "inputName": os.path.basename(input_path), "inputPath": input_path, "attemptPrep": 0, "attemptOcr": 0}
                break  # take one per tick

        # schedule PREP submissions up to PREP_CONCURRENCY
        running_prep = sum(1 for j in in_flight.values() if j["stage"] == "PREP_RUNNING")
        can_start_prep = max(0, PREP_CONCURRENCY - running_prep)
        for job_key, meta in list(in_flight.items()):
            if can_start_prep <= 0:
                break
            if meta["stage"] in ("DISCOVERED", "PREP_RETRY"):
                if meta["attemptPrep"] >= MAX_ATTEMPTS_PREP:
                    # move to error
                    update_state(job_key, {"state": "ERROR", "step": "PREP", "message": "max attempts reached"})
                    index["jobs"][job_key]["state"] = "ERROR_PREP"
                    save_index(index, index_path)
                    # move input to global error folder
                    try:
                        move_atomic(meta["inputPath"], os.path.join(ERROR_DIR, os.path.basename(meta["inputPath"])))
                    except Exception:
                        pass
                    del in_flight[job_key]
                    continue
                meta["attemptPrep"] += 1
                update_state(job_key, {"state": "PREP_SUBMITTED", "step": "PREP", "attempt": meta["attemptPrep"]})
                try:
                    submit_prep(job_key, meta["inputPath"])
                    meta["stage"] = "PREP_RUNNING"
                    index["jobs"][job_key]["state"] = "PREP_RUNNING"
                    save_index(index, index_path)
                    can_start_prep -= 1
                except Exception as e:
                    update_state(job_key, {"state": "ERROR", "step": "PREP", "message": str(e)})
                    meta["stage"] = "PREP_RETRY"
                    time.sleep(0.1)

        # poll PREP running
        for job_key, meta in list(in_flight.items()):
            if meta["stage"] != "PREP_RUNNING":
                continue
            try:
                st = poll_job(PREP_URL, job_key)
                if st.get("state") == "DONE":
                    raw_pdf = st.get("artifacts", {}).get("rawPdf") or os.path.join(job_dir(job_key), "raw.pdf")
                    update_state(job_key, {"state": "PREP_DONE", "step": "PREP", "rawPdf": raw_pdf})
                    meta["rawPdf"] = raw_pdf
                    meta["stage"] = "PREP_DONE"
                    index["jobs"][job_key]["state"] = "PREP_DONE"
                    save_index(index, index_path)
                elif st.get("state") == "ERROR":
                    update_state(job_key, {"state": "PREP_ERROR", "step": "PREP", "message": st.get("message")})
                    meta["stage"] = "PREP_RETRY"
            except Exception as e:
                # keep running; worker might be busy
                pass

        # schedule OCR submissions up to OCR_CONCURRENCY
        running_ocr = sum(1 for j in in_flight.values() if j["stage"] == "OCR_RUNNING")
        can_start_ocr = max(0, OCR_CONCURRENCY - running_ocr)
        for job_key, meta in list(in_flight.items()):
            if can_start_ocr <= 0:
                break
            if meta["stage"] in ("PREP_DONE", "OCR_RETRY"):
                if meta["attemptOcr"] >= MAX_ATTEMPTS_OCR:
                    update_state(job_key, {"state": "ERROR", "step": "OCR", "message": "max attempts reached"})
                    index["jobs"][job_key]["state"] = "ERROR_OCR"
                    save_index(index, index_path)
                    del in_flight[job_key]
                    continue
                meta["attemptOcr"] += 1
                raw_pdf = meta.get("rawPdf") or os.path.join(job_dir(job_key), "raw.pdf")
                update_state(job_key, {"state": "OCR_SUBMITTED", "step": "OCR", "attempt": meta["attemptOcr"], "rawPdf": raw_pdf})
                try:
                    submit_ocr(job_key, raw_pdf)
                    meta["stage"] = "OCR_RUNNING"
                    index["jobs"][job_key]["state"] = "OCR_RUNNING"
                    save_index(index, index_path)
                    can_start_ocr -= 1
                except Exception as e:
                    update_state(job_key, {"state": "ERROR", "step": "OCR", "message": str(e)})
                    meta["stage"] = "OCR_RETRY"
                    time.sleep(0.1)

        # poll OCR running and finalize
        for job_key, meta in list(in_flight.items()):
            if meta["stage"] != "OCR_RUNNING":
                continue
            try:
                st = poll_job(OCR_URL, job_key)
                if st.get("state") == "DONE":
                    final_pdf = st.get("artifacts", {}).get("finalPdf") or os.path.join(job_dir(job_key), "final.pdf")
                    out_pdf = output_path_for(meta["inputName"], job_key)
                    ensure_dir(OUT_DIR)
                    move_atomic(final_pdf, out_pdf)
                    update_state(job_key, {"state": "DONE", "step": "OCR", "finalPdf": out_pdf})
                    index["jobs"][job_key]["state"] = "DONE"
                    index["jobs"][job_key]["outPdf"] = out_pdf
                    save_index(index, index_path)
                    # Archive input
                    try:
                        ensure_dir(ARCHIVE_DIR)
                        move_atomic(meta["inputPath"], os.path.join(ARCHIVE_DIR, os.path.basename(meta["inputPath"])))
                    except Exception:
                        pass
                    del in_flight[job_key]
                elif st.get("state") == "ERROR":
                    update_state(job_key, {"state": "OCR_ERROR", "step": "OCR", "message": st.get("message")})
                    meta["stage"] = "OCR_RETRY"
            except Exception:
                pass

        time.sleep(POLL_INTERVAL_MS / 1000.0)

if __name__ == "__main__":
    process_loop()
