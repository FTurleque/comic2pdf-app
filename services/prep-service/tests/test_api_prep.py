import os
import sys
# Permettre l'import du package app depuis le dossier service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import subprocess
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# importer app depuis le package local
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
    assert data.get("service") == "prep-service"
    assert "versions" in data


def test_submit_job_happy_path(tmp_path, monkeypatch):
    job_id = "job-happy"
    work_dir = str(tmp_path / "work")
    os.makedirs(work_dir, exist_ok=True)

    payload = {"jobId": job_id, "inputPath": "/nonexistent/file.cbz", "workDir": work_dir}

    # Le submit doit accepter la requête et créer un fichier dans queue/
    with TestClient(app) as client:
        r = client.post("/jobs/prep", json=payload)
    assert r.status_code in (200, 202)
    # Vérifier que le fichier job.json existe dans DATA_DIR/prep/queue
    queued = os.path.join(QUEUE_DIR, f"{job_id}.json")
    assert os.path.exists(queued)
    with open(queued, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["jobId"] == job_id
    assert meta["state"] == "QUEUED"


def test_submit_job_invalid_payload():
    with TestClient(app) as client:
        r = client.post("/jobs/prep", json={})
    assert r.status_code == 422


def test_submit_job_file_absent(tmp_path):
    # submit d'un job pointant sur un fichier absent; le endpoint queue le job
    job_id = "job-missing-file"
    work_dir = str(tmp_path / "work2")
    os.makedirs(work_dir, exist_ok=True)
    payload = {"jobId": job_id, "inputPath": str(tmp_path / "no-file.cbz"), "workDir": work_dir}
    with TestClient(app) as client:
        r = client.post("/jobs/prep", json=payload)
    assert r.status_code in (200, 202)
    queued = os.path.join(QUEUE_DIR, f"{job_id}.json")
    assert os.path.exists(queued)


def test_run_job_archive_corrupted(tmp_path, monkeypatch):
    # Simule une extraction 7z qui échoue en retournant code != 0
    job_id = "job-corrupt"
    work_dir = str(tmp_path / "work3")
    os.makedirs(work_dir, exist_ok=True)
    payload = {"jobId": job_id, "inputPath": str(tmp_path / "fake.cbz"), "workDir": work_dir}

    # Créer le fichier de metadata comme fait par POST
    queue_dir = os.path.join(str(tmp_path), "prep", "queue")
    os.makedirs(os.path.join(str(tmp_path), "prep", "queue"), exist_ok=True)
    job_file = os.path.join(queue_dir, f"{job_id}.json")
    with open(job_file, "w", encoding="utf-8") as f:
        json.dump({"jobId": job_id, "inputPath": payload["inputPath"], "workDir": work_dir, "state": "QUEUED"}, f)

    # Monkeypatch subprocess.run pour renvoyer erreur
    def fake_run(cmd, capture_output=None, text=None):
        return fake_completed(returncode=1, stdout="", stderr="7z error")

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Appeler run_job sur le fichier déplacé vers running (simulate)
    running_dir = os.path.join(str(tmp_path), "prep", "running")
    os.makedirs(running_dir, exist_ok=True)
    running_job = os.path.join(running_dir, f"{job_id}.json")
    os.replace(job_file, running_job)

    with pytest.raises(Exception):
        run_job(running_job)

    # Vérifier que l'état du job est ERROR
    with open(running_job, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["state"] == "ERROR"
