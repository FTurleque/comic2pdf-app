"""
Tests du serveur HTTP d'observabilité de l'orchestrateur.
Utilise un port éphémère pour ne pas nécessiter de port fixe.
Teste GET /metrics, GET /jobs, GET /jobs/{jobKey}, POST /config, GET /config.
"""
import json
import os
import sys
import threading
import time
from http.server import HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock

from app.http_server import OrchestratorState, start_http_server
from app.core import make_empty_metrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_state(tmp_path):
    """Crée un OrchestratorState minimal avec données de test."""
    in_flight = {}
    metrics = make_empty_metrics()
    metrics["done"] = 3
    metrics["error"] = 1
    config = {
        "prep_concurrency": 2,
        "ocr_concurrency": 1,
        "job_timeout_s": 600,
    }
    index_path = str(tmp_path / "jobs.json")
    # Écrire un index minimal
    import json as _json
    with open(index_path, "w") as f:
        _json.dump({"jobs": {
            "abc__def": {
                "jobKey": "abc__def",
                "state": "DONE",
                "inputName": "comic.cbz",
                "outPdf": "/data/out/comic__job-abc__def.pdf",
                "updatedAt": "2026-01-01T00:00:00Z",
            }
        }}, f)
    state = OrchestratorState(
        in_flight=in_flight,
        metrics=metrics,
        config=config,
        work_dir=str(tmp_path / "work"),
        index_path=index_path,
    )
    return state


@pytest.fixture
def http_server(mock_state):
    """Démarre le serveur HTTP sur un port éphémère et le stoppe après le test."""
    server = start_http_server(mock_state, port=0, bind="127.0.0.1")
    yield server
    server.shutdown()


def _get(server, path: str) -> tuple:
    """Effectue une requête GET sur le serveur de test."""
    import urllib.request
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except Exception as e:
        return 500, {"error": str(e)}


def _post(server, path: str, data: dict) -> tuple:
    """Effectue une requête POST JSON sur le serveur de test."""
    import urllib.request
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return resp.status, result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


# ---------------------------------------------------------------------------
# Tests GET /metrics
# ---------------------------------------------------------------------------

class TestGetMetrics:

    def test_metrics_retourne_200(self, http_server):
        status, _ = _get(http_server, "/metrics")
        assert status == 200

    def test_metrics_contient_compteurs_requis(self, http_server):
        _, data = _get(http_server, "/metrics")
        assert "done" in data
        assert "error" in data
        assert "disk_error" in data
        assert "pdf_invalid" in data
        assert "input_rejected_size" in data
        assert "input_rejected_signature" in data

    def test_metrics_valeurs_correctes(self, http_server):
        _, data = _get(http_server, "/metrics")
        assert data["done"] == 3
        assert data["error"] == 1


# ---------------------------------------------------------------------------
# Tests GET /jobs
# ---------------------------------------------------------------------------

class TestGetJobs:

    def test_jobs_retourne_200(self, http_server):
        status, _ = _get(http_server, "/jobs")
        assert status == 200

    def test_jobs_retourne_liste(self, http_server):
        _, data = _get(http_server, "/jobs")
        assert isinstance(data, list)

    def test_jobs_contient_job_index(self, http_server):
        _, data = _get(http_server, "/jobs")
        assert len(data) >= 1
        job = next((j for j in data if j.get("jobKey") == "abc__def"), None)
        assert job is not None
        assert job["state"] == "DONE"


# ---------------------------------------------------------------------------
# Tests GET /jobs/{jobKey}
# ---------------------------------------------------------------------------

class TestGetJobByKey:

    def test_job_inconnu_retourne_404(self, http_server):
        import urllib.error
        port = http_server.server_address[1]
        url = f"http://127.0.0.1:{port}/jobs/inconnu_key"
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=5)
            pytest.fail("Devrait lever une erreur 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404

    def test_job_existant_retourne_state_json(self, http_server, tmp_path, mock_state):
        """Un job avec state.json sur disque est retourné correctement."""
        job_key = "abc__def"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True, exist_ok=True)
        state_file = job_dir / "state.json"
        state_file.write_text(json.dumps({
            "jobKey": job_key,
            "state": "DONE",
            "updatedAt": "2026-01-01T00:00:00Z",
        }))
        status, data = _get(http_server, f"/jobs/{job_key}")
        assert status == 200
        assert data["jobKey"] == job_key


# ---------------------------------------------------------------------------
# Tests POST /config
# ---------------------------------------------------------------------------

class TestPostConfig:

    def test_post_config_modifie_prep_concurrency(self, http_server, mock_state):
        status, data = _post(http_server, "/config", {"prep_concurrency": 4})
        assert status == 200
        assert data.get("applied", {}).get("prep_concurrency") == 4
        assert mock_state._config["prep_concurrency"] == 4

    def test_post_config_modifie_job_timeout(self, http_server, mock_state):
        status, data = _post(http_server, "/config", {"job_timeout_s": 1200})
        assert status == 200
        assert mock_state._config["job_timeout_s"] == 1200

    def test_post_config_payload_invalide_retourne_400(self, http_server):
        status, _ = _post(http_server, "/config", [1, 2, 3])  # pas un dict
        assert status == 400

    def test_post_config_cle_inconnue_ignoree(self, http_server, mock_state):
        """Les clés non autorisées sont ignorées sans erreur."""
        status, data = _post(http_server, "/config", {"unknown_key": "valeur"})
        assert status == 200


# ---------------------------------------------------------------------------
# Tests GET /config
# ---------------------------------------------------------------------------

class TestGetConfig:

    def test_config_retourne_200(self, http_server):
        status, _ = _get(http_server, "/config")
        assert status == 200

    def test_config_contient_prep_concurrency(self, http_server):
        _, data = _get(http_server, "/config")
        assert "prep_concurrency" in data


# ---------------------------------------------------------------------------
# Tests divers
# ---------------------------------------------------------------------------

class TestRouteInconnue:

    def test_route_inconnue_retourne_404(self, http_server):
        import urllib.error
        port = http_server.server_address[1]
        url = f"http://127.0.0.1:{port}/unknownpath"
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=5)
            pytest.fail("Devrait lever une erreur 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404

