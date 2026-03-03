import os
import sys
# Permettre l'import du package app depuis le dossier service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import subprocess
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app, QUEUE_DIR
from app.main import run_job


def fake_completed(returncode=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_get_info_ok():
    with TestClient(app) as client:
        r = client.get("/info")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "ocr-service"
    assert "versions" in data


def test_submit_job_happy_path(tmp_path):
    job_id = "job-ocr-happy"
    work_dir = str(tmp_path / "work")
    os.makedirs(work_dir, exist_ok=True)
    payload = {"jobId": job_id, "rawPdfPath": str(tmp_path / "raw.pdf"), "workDir": work_dir}

    # create a fake raw.pdf
    with open(payload["rawPdfPath"], "wb") as f:
        f.write(b"%PDF-1.4\n%fake")

    with TestClient(app) as client:
        r = client.post("/jobs/ocr", json=payload)
    assert r.status_code in (200, 202)
    queued = os.path.join(QUEUE_DIR, f"{job_id}.json")
    assert os.path.exists(queued)


def test_get_job_status(tmp_path):
    job_id = "job-status"
    work_dir = str(tmp_path / "work2")
    os.makedirs(work_dir, exist_ok=True)
    queue_dir = os.path.join(str(tmp_path), "ocr", "queue")
    os.makedirs(queue_dir, exist_ok=True)
    job_file = os.path.join(queue_dir, f"{job_id}.json")
    with open(job_file, "w", encoding="utf-8") as f:
        json.dump({"jobId": job_id, "state": "QUEUED"}, f)

    with TestClient(app) as client:
        r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["state"] == "QUEUED"


def test_submit_job_invalid_payload():
    with TestClient(app) as client:
        r = client.post("/jobs/ocr", json={})
    assert r.status_code == 422


def test_run_job_processing_failure(tmp_path, monkeypatch):
    job_id = "job-ocr-fail"
    work_dir = str(tmp_path / "work3")
    os.makedirs(work_dir, exist_ok=True)
    # create a fake raw.pdf
    raw_pdf = os.path.join(work_dir, "raw.pdf")
    with open(raw_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%fake")

    queue_dir = os.path.join(str(tmp_path), "ocr", "queue")
    os.makedirs(queue_dir, exist_ok=True)
    job_file = os.path.join(queue_dir, f"{job_id}.json")
    with open(job_file, "w", encoding="utf-8") as f:
        json.dump({"jobId": job_id, "rawPdfPath": raw_pdf, "workDir": work_dir, "state": "QUEUED"}, f)

    # move to running and simulate subprocess failure
    running_dir = os.path.join(str(tmp_path), "ocr", "running")
    os.makedirs(running_dir, exist_ok=True)
    running_job = os.path.join(running_dir, f"{job_id}.json")
    os.replace(job_file, running_job)

    def fake_run(cmd, capture_output=None, text=None):
        return fake_completed(returncode=2, stdout="", stderr="ocrmypdf failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(Exception):
        run_job(running_job)

    with open(running_job, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["state"] == "ERROR"
