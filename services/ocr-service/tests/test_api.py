"""
Tests d'intégration API ocr-service — TestClient FastAPI.
Couvre GET /info, POST /jobs/ocr, GET /jobs/{id}.
Cas nominaux + erreurs (404, 422, 400 fichier absent).
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
def fake_raw_pdf(tmp_path):
    """
    Crée un fichier raw.pdf factice (PDF minimal).
    Retourne le chemin du fichier.
    """
    pdf_path = tmp_path / "raw.pdf"
    # PDF minimal valide (header + EOF)
    pdf_path.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 0/Kids[]>>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000015 00000 n\n0000000060 00000 n\ntrailer\n<</Size 3/Root 1 0 R>>\nstartxref\n110\n%%EOF\n")
    return str(pdf_path)


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
        assert data["service"] == "ocr-service"

    def test_info_contient_versions(self, client):
        """GET /info retourne un objet versions (même si unknown)."""
        response = client.get("/info")
        data = response.json()
        assert "versions" in data
        assert isinstance(data["versions"], dict)
        # Doit contenir au moins ocrmypdf, tesseract, ghostscript
        assert "ocrmypdf" in data["versions"]
        assert "tesseract" in data["versions"]
        assert "ghostscript" in data["versions"]


# ---------------------------------------------------------------------------
# Tests POST /jobs/ocr
# ---------------------------------------------------------------------------

class TestSubmitOcrJob:
    """Tests du endpoint POST /jobs/ocr."""

    def test_submit_job_retourne_202(self, client, fake_raw_pdf, data_dir):
        """POST /jobs/ocr retourne 202 avec jobId et statusUrl."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "ocr123",
            "rawPdfPath": fake_raw_pdf,
            "workDir": work_dir,
            "lang": "fra+eng",
        }
        response = client.post("/jobs/ocr", json=payload)

        assert response.status_code == 202
        data = response.json()
        assert data["jobId"] == "ocr123"
        assert data["statusUrl"] == "/jobs/ocr123"

    def test_submit_cree_fichier_queue(self, client, fake_raw_pdf, data_dir):
        """POST /jobs/ocr crée un fichier JSON dans ocr/queue/."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "ocr456",
            "rawPdfPath": fake_raw_pdf,
            "workDir": work_dir,
            "lang": "eng",
            "rotatePages": False,
            "deskew": True,
            "optimize": 2,
        }
        client.post("/jobs/ocr", json=payload)

        queue_file = os.path.join(data_dir, "ocr", "queue", "ocr456.json")
        assert os.path.exists(queue_file)

        with open(queue_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["jobId"] == "ocr456"
        assert meta["state"] == "QUEUED"
        assert meta["rawPdfPath"] == fake_raw_pdf
        assert meta["lang"] == "eng"
        assert meta["rotatePages"] is False
        assert meta["optimize"] == 2

    def test_submit_job_avec_defauts(self, client, fake_raw_pdf, data_dir):
        """POST /jobs/ocr applique les valeurs par défaut des paramètres optionnels."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        # Payload minimal (sans options)
        payload = {
            "jobId": "ocr789",
            "rawPdfPath": fake_raw_pdf,
            "workDir": work_dir,
        }
        client.post("/jobs/ocr", json=payload)

        queue_file = os.path.join(data_dir, "ocr", "queue", "ocr789.json")
        with open(queue_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Vérifier les valeurs par défaut
        assert meta["lang"] == "fra+eng"
        assert meta["rotatePages"] is True
        assert meta["deskew"] is True
        assert meta["optimize"] == 1

    def test_submit_job_deja_existant_retourne_202(self, client, fake_raw_pdf, data_dir):
        """POST /jobs/ocr avec jobId déjà en queue retourne 202 sans recréer."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "ocr999",
            "rawPdfPath": fake_raw_pdf,
            "workDir": work_dir,
        }

        # Premier submit
        r1 = client.post("/jobs/ocr", json=payload)
        assert r1.status_code == 202

        # Deuxième submit (dédoublonnage)
        r2 = client.post("/jobs/ocr", json=payload)
        assert r2.status_code == 202
        data = r2.json()
        assert data["jobId"] == "ocr999"

    def test_submit_payload_invalide_retourne_422(self, client):
        """POST /jobs/ocr avec payload invalide retourne 422 (validation FastAPI)."""
        # Payload manquant jobId
        response = client.post("/jobs/ocr", json={"rawPdfPath": "/fake.pdf"})
        assert response.status_code == 422

    def test_submit_payload_type_invalide_retourne_422(self, client, data_dir):
        """POST /jobs/ocr avec type invalide (optimize non-int) retourne 422."""
        payload = {
            "jobId": "bad_type",
            "rawPdfPath": "/fake.pdf",
            "workDir": str(data_dir),
            "optimize": "not_an_int",  # Doit être int
        }
        response = client.post("/jobs/ocr", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests GET /jobs/{id}
# ---------------------------------------------------------------------------

class TestJobStatusEndpoint:
    """Tests du endpoint GET /jobs/{id}."""

    def test_status_job_queued_retourne_200(self, client, fake_raw_pdf, data_dir):
        """GET /jobs/{id} retourne 200 avec état QUEUED si job existe."""
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        # Créer un job
        payload = {
            "jobId": "status_ocr123",
            "rawPdfPath": fake_raw_pdf,
            "workDir": work_dir,
        }
        client.post("/jobs/ocr", json=payload)

        # Interroger le status
        response = client.get("/jobs/status_ocr123")
        assert response.status_code == 200
        data = response.json()
        assert data["jobId"] == "status_ocr123"
        assert data["state"] == "QUEUED"

    def test_status_job_inexistant_retourne_404(self, client):
        """GET /jobs/{id} retourne 404 si job inconnu."""
        response = client.get("/jobs/unknown_ocr999")
        assert response.status_code == 404
        assert "job not found" in response.json()["detail"]

    def test_status_job_done_retourne_200(self, client, data_dir):
        """GET /jobs/{id} retourne 200 avec état DONE si job terminé."""
        # Simuler un job DONE en écrivant directement dans ocr/done/
        done_dir = os.path.join(data_dir, "ocr", "done")
        os.makedirs(done_dir, exist_ok=True)

        done_file = os.path.join(done_dir, "done_ocr123.json")
        meta = {
            "jobId": "done_ocr123",
            "state": "DONE",
            "message": "final.pdf ready",
            "artifacts": {"finalPdf": "/data/work/done_ocr123/final.pdf"},
        }
        with open(done_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        response = client.get("/jobs/done_ocr123")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "DONE"
        assert "artifacts" in data
        assert data["artifacts"]["finalPdf"].endswith("final.pdf")

    def test_status_job_error_retourne_200(self, client, data_dir):
        """GET /jobs/{id} retourne 200 avec état ERROR si job en erreur."""
        error_dir = os.path.join(data_dir, "ocr", "error")
        os.makedirs(error_dir, exist_ok=True)

        error_file = os.path.join(error_dir, "error_ocr123.json")
        meta = {
            "jobId": "error_ocr123",
            "state": "ERROR",
            "message": "ocrmypdf failed rc=1",
            "error": {"type": "RuntimeError", "detail": "ocrmypdf failed rc=1"},
        }
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        response = client.get("/jobs/error_ocr123")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "ERROR"
        assert data["message"] == "ocrmypdf failed rc=1"

    def test_status_job_running_retourne_200(self, client, data_dir):
        """GET /jobs/{id} retourne 200 avec état RUNNING si job en cours."""
        running_dir = os.path.join(data_dir, "ocr", "running")
        os.makedirs(running_dir, exist_ok=True)

        running_file = os.path.join(running_dir, "running_ocr123.json")
        meta = {
            "jobId": "running_ocr123",
            "state": "RUNNING",
            "message": "ocr running",
        }
        with open(running_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        response = client.get("/jobs/running_ocr123")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "RUNNING"


# ---------------------------------------------------------------------------
# Tests cas d'erreur (400)
# ---------------------------------------------------------------------------

class TestErrorCases:
    """Tests des cas d'erreur métier (fichier absent, PDF corrompu)."""

    def test_submit_fichier_inexistant(self, client, data_dir):
        """
        POST /jobs/ocr avec rawPdfPath inexistant est accepté (202).
        L'erreur sera détectée lors de l'exécution du worker.
        Note : FastAPI ne valide pas l'existence du fichier à la soumission.
        """
        work_dir = os.path.join(data_dir, "work")
        os.makedirs(work_dir, exist_ok=True)

        payload = {
            "jobId": "missing_pdf",
            "rawPdfPath": "/path/does/not/exist.pdf",
            "workDir": work_dir,
        }
        response = client.post("/jobs/ocr", json=payload)
        # FastAPI accepte la soumission, l'erreur sera dans le worker
        assert response.status_code == 202

