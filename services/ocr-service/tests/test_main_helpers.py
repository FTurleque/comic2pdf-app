"""
Tests des fonctions helpers — ocr-service main.py.
Couvre claim_one, update_state (identiques à prep-service).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Tests claim_one
# ---------------------------------------------------------------------------

class TestClaimOne:
    """Tests de la fonction claim_one."""

    def test_claim_one_returns_job_from_queue(self, tmp_path, monkeypatch):
        """claim_one déplace un job de queue/ vers running/ et retourne le chemin."""
        from app.main import claim_one

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        job_file = queue_dir / "job1.json"
        job_file.write_text('{"jobId": "job1", "state": "QUEUED"}')

        result = claim_one()

        assert result == str(running_dir / "job1.json")
        assert not job_file.exists()
        assert (running_dir / "job1.json").exists()

    def test_claim_one_returns_none_if_queue_empty(self, tmp_path, monkeypatch):
        """claim_one retourne None si la file est vide."""
        from app.main import claim_one

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        result = claim_one()

        assert result is None

    def test_claim_one_ignores_non_json(self, tmp_path, monkeypatch):
        """claim_one ignore les fichiers non-.json."""
        from app.main import claim_one

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        (queue_dir / "readme.txt").write_text("not a job")

        result = claim_one()

        assert result is None

    def test_claim_one_creates_dirs_if_missing(self, tmp_path, monkeypatch):
        """claim_one crée les dossiers s'ils n'existent pas."""
        from app.main import claim_one

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        claim_one()

        assert queue_dir.exists()
        assert running_dir.exists()


# ---------------------------------------------------------------------------
# Tests update_state
# ---------------------------------------------------------------------------

class TestUpdateState:
    """Tests de la fonction update_state."""

    def test_update_state_updates_json(self, tmp_path):
        """update_state met à jour le fichier JSON avec les nouveaux champs."""
        from app.main import update_state

        job_file = tmp_path / "job1.json"
        job_file.write_text('{"jobId": "job1", "state": "QUEUED"}')

        update_state(str(job_file), {"state": "RUNNING", "progress": 75})

        with open(job_file, "r") as f:
            data = json.load(f)

        assert data["jobId"] == "job1"
        assert data["state"] == "RUNNING"
        assert data["progress"] == 75
        assert "updatedAt" in data

    def test_update_state_creates_file_if_missing(self, tmp_path):
        """update_state crée le fichier s'il n'existe pas."""
        from app.main import update_state

        job_file = tmp_path / "job_new.json"

        update_state(str(job_file), {"state": "RUNNING"})

        assert job_file.exists()

    def test_update_state_adds_timestamp(self, tmp_path):
        """update_state ajoute automatiquement updatedAt."""
        from app.main import update_state

        job_file = tmp_path / "job1.json"
        job_file.write_text('{"jobId": "job1"}')

        update_state(str(job_file), {"state": "RUNNING"})

        with open(job_file, "r") as f:
            data = json.load(f)

        assert "updatedAt" in data
        assert "T" in data["updatedAt"]
        assert "Z" in data["updatedAt"]

