import os
import threading
import time
import json
import sys

# Allow importing app package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app import main as m


def test_submit_with_simulated_worker(tmp_path, monkeypatch):
    # Use isolated DATA_DIR
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Ensure builtin workers are disabled; we'll simulate our own worker
    monkeypatch.setenv("DISABLE_WORKERS", "1")

    job_id = "job-sim"
    work_dir = os.path.join(str(tmp_path), "work")
    os.makedirs(work_dir, exist_ok=True)

    start_evt = threading.Event()
    finished_evt = threading.Event()

    def simulated_worker():
        # Wait until allowed to run
        start_evt.wait()
        # Try to claim one job and mark it RUNNING (simulate processing)
        try:
            claimed = m.claim_one()
            if claimed:
                # Update state to RUNNING
                m.update_state(claimed, {"state": "RUNNING", "message": "simulated"})
        finally:
            finished_evt.set()

    t = threading.Thread(target=simulated_worker, daemon=True)
    t.start()

    # Post the job via TestClient
    payload = {"jobId": job_id, "inputPath": "/no/such.cbz", "workDir": work_dir}
    with TestClient(m.app) as client:
        r = client.post("/jobs/prep", json=payload)
        assert r.status_code in (200, 202)

    # Path to queued file
    qpath = os.path.join(os.fspath(m.QUEUE_DIR), f"{job_id}.json")
    assert os.path.exists(qpath), "queued file must exist"
    with open(qpath, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta.get("state") == "QUEUED", "submit must create job in QUEUED state"

    # Now allow worker to run and finish
    # Wait for the small grace window used by claim_one (0.05s) to elapse
    time.sleep(0.06)
    start_evt.set()
    finished_evt.wait(timeout=2)

    # After worker runs, job should have been moved to running
    rpath = os.path.join(os.fspath(m.RUNNING_DIR), f"{job_id}.json")
    assert os.path.exists(rpath), "job should be moved to running by worker"
    with open(rpath, "r", encoding="utf-8") as f:
        meta2 = json.load(f)
    assert meta2.get("state") in ("RUNNING", "ERROR", "DONE"), "worker updated state"

