"""
Tests des fonctions helpers — prep-service main.py.
Couvre claim_one, update_state, requeue_running_on_startup.
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

        # Créer un job dans queue
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

        # Créer fichier .txt
        (queue_dir / "readme.txt").write_text("not a job")

        result = claim_one()

        assert result is None
        assert (queue_dir / "readme.txt").exists()

    def test_claim_one_handles_concurrent_access(self, tmp_path, monkeypatch):
        """claim_one gère la concurrence (fichier déjà déplacé)."""
        from app.main import claim_one

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        # Créer 2 jobs
        (queue_dir / "job1.json").write_text('{"jobId": "job1"}')
        (queue_dir / "job2.json").write_text('{"jobId": "job2"}')

        # Supprimer job1 avant claim (simule concurrence)
        os.remove(queue_dir / "job1.json")

        result = claim_one()

        # Doit retourner job2
        assert result == str(running_dir / "job2.json")

    def test_claim_one_creates_dirs_if_missing(self, tmp_path, monkeypatch):
        """claim_one crée les dossiers queue/ et running/ s'ils n'existent pas."""
        from app.main import claim_one

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        # Dossiers n'existent pas
        assert not queue_dir.exists()
        assert not running_dir.exists()

        claim_one()

        # Dossiers créés
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

        update_state(str(job_file), {"state": "RUNNING", "progress": 50})

        with open(job_file, "r") as f:
            data = json.load(f)

        assert data["jobId"] == "job1"
        assert data["state"] == "RUNNING"
        assert data["progress"] == 50
        assert "updatedAt" in data

    def test_update_state_creates_file_if_missing(self, tmp_path):
        """update_state crée le fichier s'il n'existe pas."""
        from app.main import update_state

        job_file = tmp_path / "job_new.json"

        update_state(str(job_file), {"state": "RUNNING"})

        assert job_file.exists()
        with open(job_file, "r") as f:
            data = json.load(f)

        assert data["state"] == "RUNNING"
        assert "updatedAt" in data

    def test_update_state_preserves_existing_fields(self, tmp_path):
        """update_state préserve les champs existants non modifiés."""
        from app.main import update_state

        job_file = tmp_path / "job1.json"
        job_file.write_text('{"jobId": "job1", "state": "QUEUED", "custom": "value"}')

        update_state(str(job_file), {"state": "RUNNING"})

        with open(job_file, "r") as f:
            data = json.load(f)

        assert data["jobId"] == "job1"
        assert data["custom"] == "value"
        assert data["state"] == "RUNNING"

    def test_update_state_is_atomic(self, tmp_path):
        """update_state utilise atomic_write_json (fichier .tmp)."""
        from app.main import update_state

        job_file = tmp_path / "job1.json"
        job_file.write_text('{"jobId": "job1"}')
        tmp_file = tmp_path / "job1.json.tmp"

        update_state(str(job_file), {"state": "DONE"})

        # Fichier .tmp ne doit pas exister après
        assert not tmp_file.exists()
        assert job_file.exists()

    def test_update_state_adds_timestamp(self, tmp_path):
        """update_state ajoute automatiquement updatedAt."""
        from app.main import update_state
        import time

        job_file = tmp_path / "job1.json"
        job_file.write_text('{"jobId": "job1"}')

        before = time.time()
        update_state(str(job_file), {"state": "RUNNING"})
        after = time.time()

        with open(job_file, "r") as f:
            data = json.load(f)

        assert "updatedAt" in data
        # Format ISO
        assert "T" in data["updatedAt"]
        assert "Z" in data["updatedAt"]


# ---------------------------------------------------------------------------
# Tests requeue_running_on_startup
# ---------------------------------------------------------------------------

class TestRequeueRunningOnStartup:
    """Tests de la fonction requeue_running_on_startup."""

    def test_requeue_moves_jobs_from_running_to_queue(self, tmp_path, monkeypatch):
        """requeue_running_on_startup déplace tous les .json de running/ vers queue/."""
        from app.main import requeue_running_on_startup

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        # Créer 3 jobs dans running
        for i in range(3):
            (running_dir / f"job{i}.json").write_text(f'{{"jobId": "job{i}"}}')

        requeue_running_on_startup()

        # Tous déplacés vers queue
        assert len(list(running_dir.glob("*.json"))) == 0
        assert len(list(queue_dir.glob("*.json"))) == 3

    def test_requeue_ignores_non_json(self, tmp_path, monkeypatch):
        """requeue_running_on_startup ignore les fichiers non-.json."""
        from app.main import requeue_running_on_startup

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        (running_dir / "job1.json").write_text('{"jobId": "job1"}')
        (running_dir / "readme.txt").write_text("ignore me")

        requeue_running_on_startup()

        assert (queue_dir / "job1.json").exists()
        assert (running_dir / "readme.txt").exists()
        assert not (queue_dir / "readme.txt").exists()

    def test_requeue_handles_empty_running_dir(self, tmp_path, monkeypatch):
        """requeue_running_on_startup gère un dossier running vide."""
        from app.main import requeue_running_on_startup

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        # Pas d'exception levée
        requeue_running_on_startup()

        assert len(list(running_dir.glob("*"))) == 0

    def test_requeue_creates_dirs_if_missing(self, tmp_path, monkeypatch):
        """requeue_running_on_startup crée les dossiers s'ils n'existent pas."""
        from app.main import requeue_running_on_startup

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        requeue_running_on_startup()

        assert queue_dir.exists()
        assert running_dir.exists()

    def test_requeue_handles_exception_gracefully(self, tmp_path, monkeypatch):
        """requeue_running_on_startup continue même si un fichier échoue."""
        from app.main import requeue_running_on_startup

        queue_dir = tmp_path / "queue"
        running_dir = tmp_path / "running"
        queue_dir.mkdir()
        running_dir.mkdir()

        monkeypatch.setattr("app.main.QUEUE_DIR", str(queue_dir))
        monkeypatch.setattr("app.main.RUNNING_DIR", str(running_dir))

        # Créer jobs
        (running_dir / "job1.json").write_text('{"jobId": "job1"}')
        (running_dir / "job2.json").write_text('{"jobId": "job2"}')

        # Créer job1 dans queue pour forcer conflit
        (queue_dir / "job1.json").write_text('{"jobId": "job1_old"}')

        # Ne doit pas lever d'exception
        requeue_running_on_startup()

        # Au moins job2 doit être déplacé
        assert (queue_dir / "job2.json").exists()

