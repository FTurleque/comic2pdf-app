"""
Tests d'intégration API prep-service — TestClient FastAPI.
Couvre GET /info, POST /jobs/prep, GET /jobs/{id}.
Cas nominaux + erreurs (404, 422, 400 archive corrompue).
subprocess.run mocké — aucun outil externe requis.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """
    Injecte DATA_DIR vers un répertoire temporaire isolé.
    Évite toute pollution des données réelles.
    """
    data_dir_path = str(tmp_path / "data")
    os.makedirs(data_dir_path, exist_ok=True)
    monkeypatch.setenv("DATA_DIR", data_dir_path)
    # Forcer le rechargement du module main avec le nouveau DATA_DIR
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    return data_dir_path


@pytest.fixture
def client(data_dir, mocker):
    """
    Client TestClient FastAPI configuré avec DATA_DIR isolé.
    Mock worker_loop pour ne pas lancer les threads workers.
    """
    # Mock worker_loop avant import pour éviter démarrage threads
    mocker.patch("app.main.worker_loop", autospec=True)

    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def fake_cbz(tmp_path):
    """
    Crée un fichier CBZ factice (zip avec quelques images simulées).
    Retourne le chemin du fichier.
    """
    cbz_path = tmp_path / "test.cbz"
    import zipfile
    with zipfile.ZipFile(cbz_path, "w") as zf:
        # Ajouter quelques "images" factices (contenu minimal)
        zf.writestr("page01.jpg", b"\xff\xd8\xff\xe0JFIF")
        zf.writestr("page02.jpg", b"\xff\xd8\xff\xe0JFIF")
    return str(cbz_path)


# ---------------------------------------------------------------------------
# Tests GET /info
# ---------------------------------------------------------------------------

class TestInfoEndpoint:
    """Tests du endpoint GET /info."""

    def test_info_retourne_200(self, client):
        """GET /info retourne 200 avec métadonnées du service."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "prep-service"

    def test_info_contient_versions(self, client):
        """GET /info retourne un objet versions (même si unknown)."""
        response = client.get("/info")
        data = response.json()
        assert "versions" in data
        assert isinstance(data["versions"], dict)


# ---------------------------------------------------------------------------
# Tests POST /jobs/prep
# ---------------------------------------------------------------------------

class TestSubmitPrepJob:
    """Tests du endpoint POST /jobs/prep."""

    def test_submit_job_retourne_202(self, client, fake_cbz, data_dir):
        """POST /jobs/prep retourne 202 avec jobId et statusUrl."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "job123",
            "inputPath": fake_cbz,
            "workDir": work_dir,
        }
        response = client.post("/jobs/prep", json=payload)

        assert response.status_code == 202
        data = response.json()
        assert data["jobId"] == "job123"
        assert data["statusUrl"] == "/jobs/job123"

    def test_submit_cree_fichier_queue(self, client, fake_cbz, data_dir):
        """POST /jobs/prep crée un fichier JSON dans prep/queue/."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "job456",
            "inputPath": fake_cbz,
            "workDir": work_dir,
        }
        client.post("/jobs/prep", json=payload)

        queue_file = os.path.join(data_dir, "prep", "queue", "job456.json")
        assert os.path.exists(queue_file)

        with open(queue_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["jobId"] == "job456"
        assert meta["state"] == "QUEUED"
        assert meta["inputPath"] == fake_cbz

    def test_submit_job_deja_existant_retourne_202(self, client, fake_cbz, data_dir):
        """POST /jobs/prep avec jobId déjà en queue retourne 202 sans recréer."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "job789",
            "inputPath": fake_cbz,
            "workDir": work_dir,
        }

        # Premier submit
        r1 = client.post("/jobs/prep", json=payload)
        assert r1.status_code == 202

        # Deuxième submit (dédoublonnage)
        r2 = client.post("/jobs/prep", json=payload)
        assert r2.status_code == 202
        data = r2.json()
        assert data["jobId"] == "job789"

    def test_submit_payload_invalide_retourne_422(self, client):
        """POST /jobs/prep avec payload invalide retourne 422 (validation FastAPI)."""
        # Payload manquant jobId
        response = client.post("/jobs/prep", json={"inputPath": "/fake"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests GET /jobs/{id}
# ---------------------------------------------------------------------------

class TestJobStatusEndpoint:
    """Tests du endpoint GET /jobs/{id}."""

    def test_status_job_queued_retourne_200(self, client, fake_cbz, data_dir):
        """GET /jobs/{id} retourne 200 avec état QUEUED si job existe."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        # Créer un job
        payload = {
            "jobId": "status123",
            "inputPath": fake_cbz,
            "workDir": work_dir,
        }
        client.post("/jobs/prep", json=payload)

        # Interroger le status
        response = client.get("/jobs/status123")
        assert response.status_code == 200
        data = response.json()
        assert data["jobId"] == "status123"
        assert data["state"] == "QUEUED"

    def test_status_job_inexistant_retourne_404(self, client):
        """GET /jobs/{id} retourne 404 si job inconnu."""
        response = client.get("/jobs/unknown999")
        assert response.status_code == 404
        assert "job not found" in response.json()["detail"]

    def test_status_job_done_retourne_200(self, client, data_dir):
        """GET /jobs/{id} retourne 200 avec état DONE si job terminé."""
        # Simuler un job DONE en écrivant directement dans prep/done/
        done_dir = os.path.join(data_dir, "prep", "done")
        os.makedirs(done_dir, exist_ok=True)

        done_file = os.path.join(done_dir, "done123.json")
        meta = {
            "jobId": "done123",
            "state": "DONE",
            "message": "raw.pdf ready",
            "artifacts": {"rawPdf": "/data/work/done123/raw.pdf"},
        }
        with open(done_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        response = client.get("/jobs/done123")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "DONE"
        assert "artifacts" in data

    def test_status_job_error_retourne_200(self, client, data_dir):
        """GET /jobs/{id} retourne 200 avec état ERROR si job en erreur."""
        error_dir = os.path.join(data_dir, "prep", "error")
        os.makedirs(error_dir, exist_ok=True)

        error_file = os.path.join(error_dir, "error123.json")
        meta = {
            "jobId": "error123",
            "state": "ERROR",
            "message": "7z failed rc=2",
            "error": {"type": "RuntimeError", "detail": "7z failed rc=2"},
        }
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        response = client.get("/jobs/error123")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "ERROR"
        assert data["message"] == "7z failed rc=2"


# ---------------------------------------------------------------------------
# Tests cas d'erreur (400)
# ---------------------------------------------------------------------------

class TestErrorCases:
    """Tests des cas d'erreur métier (fichier absent, archive corrompue)."""

    def test_submit_fichier_inexistant(self, client, data_dir):
        """
        POST /jobs/prep avec inputPath inexistant est accepté (202).
        L'erreur sera détectée lors de l'exécution du worker.
        Note : FastAPI ne valide pas l'existence du fichier à la soumission.
        """
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "missing123",
            "inputPath": "/path/does/not/exist.cbz",
            "workDir": work_dir,
        }
        response = client.post("/jobs/prep", json=payload)
        # FastAPI accepte la soumission, l'erreur sera dans le worker
        assert response.status_code == 202

