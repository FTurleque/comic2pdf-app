"""
Tests d'authentification sur POST /config de l'orchestrateur.

Scénarios couverts :
  - ORCHESTRATOR_API_KEY définie + bonne clé  → 200
  - ORCHESTRATOR_API_KEY définie + mauvaise clé → 401
  - ORCHESTRATOR_API_KEY définie + header absent → 401
  - ORCHESTRATOR_API_KEY non définie + localhost → 200
  - ORCHESTRATOR_API_KEY non définie + IP externe (simulée) → 403
  - GET /config reste accessible sans auth (lecture seule)
  - GET /jobs reste accessible sans auth
  - GET /metrics reste accessible sans auth

Note : les tests patchent os.environ pour simuler la présence/absence de la clé.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

from app.http_server import OrchestratorState, start_http_server
from app.core import make_empty_metrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_state(tmp_path):
    """Crée un OrchestratorState minimal pour les tests d'auth."""
    index_path = str(tmp_path / "jobs.json")
    with open(index_path, "w") as f:
        json.dump({"jobs": {}}, f)

    return OrchestratorState(
        in_flight={},
        metrics=make_empty_metrics(),
        config={"prep_concurrency": 2, "ocr_concurrency": 1, "job_timeout_s": 600},
        work_dir=str(tmp_path / "work"),
        index_path=index_path,
    )


@pytest.fixture
def http_server(mock_state):
    """Serveur HTTP sur port éphémère, arrêté après le test."""
    server = start_http_server(mock_state, port=0, bind="127.0.0.1")
    yield server
    server.shutdown()


def _get(server, path: str) -> tuple:
    """GET sur le serveur de test. Retourne (status_code, body_dict)."""
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


def _post(server, path: str, data: dict, headers: dict = None) -> tuple:
    """POST JSON sur le serveur de test avec headers optionnels."""
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{path}"
    body = json.dumps(data).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


# ---------------------------------------------------------------------------
# Tests : ORCHESTRATOR_API_KEY définie
# ---------------------------------------------------------------------------

class TestAvecCleConfiguree:
    """Tests avec ORCHESTRATOR_API_KEY définie."""

    def test_post_config_bonne_cle_retourne_200(self, http_server):
        """POST /config avec la bonne clé → 200."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "ma-cle-secrete"}):
            status, data = _post(http_server, "/config",
                                 {"prep_concurrency": 3},
                                 headers={"X-Api-Key": "ma-cle-secrete"})
        assert status == 200
        assert data.get("applied", {}).get("prep_concurrency") == 3

    def test_post_config_mauvaise_cle_retourne_401(self, http_server):
        """POST /config avec une mauvaise clé → 401."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "ma-cle-secrete"}):
            status, data = _post(http_server, "/config",
                                 {"prep_concurrency": 3},
                                 headers={"X-Api-Key": "mauvaise-cle"})
        assert status == 401
        assert "error" in data

    def test_post_config_header_absent_retourne_401(self, http_server):
        """POST /config sans header X-Api-Key → 401."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "ma-cle-secrete"}):
            status, data = _post(http_server, "/config", {"prep_concurrency": 3})
        assert status == 401

    def test_post_config_header_vide_retourne_401(self, http_server):
        """POST /config avec header vide → 401."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "ma-cle-secrete"}):
            status, data = _post(http_server, "/config",
                                 {"prep_concurrency": 3},
                                 headers={"X-Api-Key": ""})
        assert status == 401


# ---------------------------------------------------------------------------
# Tests : ORCHESTRATOR_API_KEY non définie (comportement localhost-only)
# ---------------------------------------------------------------------------

class TestSansCleConfiguree:
    """Tests sans ORCHESTRATOR_API_KEY (comportement fallback localhost)."""

    def test_post_config_depuis_localhost_retourne_200(self, http_server):
        """POST /config depuis localhost sans clé configurée → 200 (localhost autorisé)."""
        with patch.dict(os.environ, {}, clear=False):
            # Supprimer la clé si elle existait
            env_sans_cle = {k: v for k, v in os.environ.items()
                           if k != "ORCHESTRATOR_API_KEY"}
            with patch.dict(os.environ, env_sans_cle, clear=True):
                status, data = _post(http_server, "/config", {"prep_concurrency": 2})
        assert status == 200

    def test_post_config_ip_externe_retourne_403(self, http_server, mock_state):
        """POST /config depuis une IP non-locale sans clé configurée → 403."""
        env_sans_cle = {k: v for k, v in os.environ.items()
                       if k != "ORCHESTRATOR_API_KEY"}
        with patch.dict(os.environ, env_sans_cle, clear=True):
            # Simuler une IP externe en patchant client_address
            from app.http_server import _OrchestratorHandler
            with patch.object(_OrchestratorHandler, '_get_client_ip',
                              return_value="192.168.1.100"):
                status, data = _post(http_server, "/config", {"prep_concurrency": 2})
        assert status == 403
        assert "error" in data


# ---------------------------------------------------------------------------
# Tests : GET endpoints restent sans auth
# ---------------------------------------------------------------------------

class TestGetEndpointsSansAuth:
    """Vérification que les endpoints GET sont toujours accessibles sans auth."""

    def test_get_config_accessible_sans_auth(self, http_server):
        """GET /config ne requiert aucune authentification."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "une-cle"}):
            status, data = _get(http_server, "/config")
        assert status == 200

    def test_get_jobs_accessible_sans_auth(self, http_server):
        """GET /jobs ne requiert aucune authentification."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "une-cle"}):
            status, data = _get(http_server, "/jobs")
        assert status == 200
        assert isinstance(data, list)

    def test_get_metrics_accessible_sans_auth(self, http_server):
        """GET /metrics ne requiert aucune authentification."""
        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "une-cle"}):
            status, data = _get(http_server, "/metrics")
        assert status == 200


# ---------------------------------------------------------------------------
# Tests : logs d'audit
# ---------------------------------------------------------------------------

class TestAuditLogs:
    """Vérification des logs d'audit (appel accepté / refusé loggué).

    Le logger orchestrator.http utilise un StreamHandler (stderr) configuré par get_logger().
    On intercepte les appels au logger directement via unittest.mock.patch.object.
    """

    def test_post_config_bonne_cle_log_accepted(self, http_server):
        """Un POST accepté appelle logger.info avec 'ACCEPTED'."""
        import logging
        import app.http_server as http_mod
        logged_messages = []

        original_info = http_mod._log.info
        def capture_info(msg, *args, **kwargs):
            logged_messages.append(msg)
            original_info(msg, *args, **kwargs)

        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "cle-audit"}):
            with patch.object(http_mod._log, "info", side_effect=capture_info):
                _post(http_server, "/config",
                      {"prep_concurrency": 2},
                      headers={"X-Api-Key": "cle-audit"})

        assert any("ACCEPTED" in m for m in logged_messages), \
            f"Un log ACCEPTED doit être émis lors d'une auth réussie. Messages: {logged_messages}"

    def test_post_config_mauvaise_cle_log_refused(self, http_server):
        """Un POST refusé appelle logger.warning avec 'REFUSED'."""
        import app.http_server as http_mod
        logged_messages = []

        original_warning = http_mod._log.warning
        def capture_warning(msg, *args, **kwargs):
            logged_messages.append(msg)
            original_warning(msg, *args, **kwargs)

        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": "cle-audit"}):
            with patch.object(http_mod._log, "warning", side_effect=capture_warning):
                _post(http_server, "/config",
                      {"prep_concurrency": 2},
                      headers={"X-Api-Key": "mauvaise"})

        assert any("REFUSED" in m for m in logged_messages), \
            f"Un log REFUSED doit être émis lors d'une auth échouée. Messages: {logged_messages}"

    def test_log_ne_contient_pas_valeur_cle(self, http_server):
        """La valeur de la clé API ne doit jamais apparaître dans les logs."""
        import app.http_server as http_mod
        all_messages = []
        SECRET = "CLE-ULTRA-SECRETE-XYZ"

        def capture_any(msg, *a, **kw):
            all_messages.append(str(msg))

        with patch.dict(os.environ, {"ORCHESTRATOR_API_KEY": SECRET}):
            with patch.object(http_mod._log, "info", side_effect=capture_any), \
                 patch.object(http_mod._log, "warning", side_effect=capture_any), \
                 patch.object(http_mod._log, "error", side_effect=capture_any):
                _post(http_server, "/config",
                      {"prep_concurrency": 2},
                      headers={"X-Api-Key": SECRET})

        for msg in all_messages:
            assert SECRET not in msg, \
                f"La valeur de la clé API ne doit JAMAIS apparaître dans les logs. Message: {msg}"


