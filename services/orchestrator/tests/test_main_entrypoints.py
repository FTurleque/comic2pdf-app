"""
Tests des entrypoints de l'orchestrateur :
  ensure_layout, get_service_info, submit_prep, submit_ocr, poll_job,
  check_duplicate_decisions (USE_EXISTING_RESULT / DISCARD / FORCE_REPROCESS),
  process_loop (stoppé via side_effect=[None, StopIteration] sur process_tick).

HTTP entièrement mocké via unittest.mock.patch.
Aucun réseau, aucun sleep réel, aucune boucle infinie.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
import app.main as _orch
from app.utils import atomic_write_json, ensure_dir, now_iso


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _setup_dirs(tmp_path):
    """Crée l'arborescence de données minimale."""
    for d in ["in", "out", "work", "error", "archive",
              "hold/duplicates", "reports/duplicates", "index"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)


def _patch_dirs(tmp_path, monkeypatch):
    """Patche tous les répertoires globaux de l'orchestrateur."""
    monkeypatch.setattr(_orch, "IN_DIR",         str(tmp_path / "in"))
    monkeypatch.setattr(_orch, "OUT_DIR",         str(tmp_path / "out"))
    monkeypatch.setattr(_orch, "WORK_DIR",        str(tmp_path / "work"))
    monkeypatch.setattr(_orch, "ERROR_DIR",       str(tmp_path / "error"))
    monkeypatch.setattr(_orch, "ARCHIVE_DIR",     str(tmp_path / "archive"))
    monkeypatch.setattr(_orch, "HOLD_DUP_DIR",    str(tmp_path / "hold" / "duplicates"))
    monkeypatch.setattr(_orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
    monkeypatch.setattr(_orch, "INDEX_DIR",       str(tmp_path / "index"))


def _fake_response(status_code=200, json_data=None):
    """Crée un mock de réponse HTTP requests."""
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_data or {}
    m.text = str(json_data or {})
    return m


# ---------------------------------------------------------------------------
# Tests ensure_layout
# ---------------------------------------------------------------------------

class TestEnsureLayout:
    """Tests de la fonction ensure_layout."""

    def test_cree_tous_les_dossiers(self, tmp_path, monkeypatch):
        """ensure_layout crée tous les répertoires nécessaires s'ils sont absents."""
        _patch_dirs(tmp_path, monkeypatch)
        import shutil
        shutil.rmtree(str(tmp_path / "out"), ignore_errors=True)
        shutil.rmtree(str(tmp_path / "archive"), ignore_errors=True)

        _orch.ensure_layout()

        assert (tmp_path / "out").exists()
        assert (tmp_path / "archive").exists()
        assert (tmp_path / "hold" / "duplicates").exists()
        assert (tmp_path / "reports" / "duplicates").exists()
        assert (tmp_path / "index").exists()

    def test_idempotent(self, tmp_path, monkeypatch):
        """ensure_layout peut être appelé deux fois sans erreur."""
        _setup_dirs(tmp_path)
        _patch_dirs(tmp_path, monkeypatch)

        _orch.ensure_layout()
        _orch.ensure_layout()  # Deuxième appel — ne doit pas lever d'exception


# ---------------------------------------------------------------------------
# Tests get_service_info
# ---------------------------------------------------------------------------

class TestGetServiceInfo:
    """Tests de la fonction get_service_info."""

    def test_ok_retourne_json(self):
        """get_service_info retourne le JSON du service si la requête réussit."""
        fake = _fake_response(200, {"service": "prep-service", "versions": {"7z": "23.01"}})
        with patch("app.main.requests.get", return_value=fake):
            result = _orch.get_service_info("http://mock-prep:8080")

        assert result["service"] == "prep-service"
        assert "versions" in result

    def test_exception_retourne_minimal(self):
        """get_service_info retourne un dict minimal en cas d'erreur réseau."""
        with patch("app.main.requests.get", side_effect=ConnectionError("refused")):
            result = _orch.get_service_info("http://unreachable:8080")

        assert "service" in result
        assert "versions" in result

    def test_timeout_retourne_minimal(self):
        """get_service_info retourne un dict minimal en cas de timeout."""
        with patch("app.main.requests.get", side_effect=TimeoutError("timeout")):
            result = _orch.get_service_info("http://slow:8080")

        assert isinstance(result, dict)
        assert "versions" in result


# ---------------------------------------------------------------------------
# Tests submit_prep
# ---------------------------------------------------------------------------

class TestSubmitPrep:
    """Tests de la fonction submit_prep."""

    def test_ok_202_ne_leve_pas(self):
        """submit_prep avec réponse 202 ne lève pas d'exception."""
        with patch("app.main.requests.post", return_value=_fake_response(202)):
            _orch.submit_prep("key123", "/data/work/key123/comic.cbz")

    def test_ok_200_ne_leve_pas(self):
        """submit_prep avec réponse 200 ne lève pas d'exception."""
        with patch("app.main.requests.post", return_value=_fake_response(200)):
            _orch.submit_prep("key123", "/data/comic.cbz")

    def test_erreur_500_leve_runtime(self):
        """submit_prep avec réponse 500 lève RuntimeError."""
        with patch("app.main.requests.post", return_value=_fake_response(500, {"error": "srv err"})):
            with pytest.raises(RuntimeError, match="prep submit failed"):
                _orch.submit_prep("key123", "/data/comic.cbz")

    def test_erreur_400_leve_runtime(self):
        """submit_prep avec réponse 400 lève RuntimeError."""
        with patch("app.main.requests.post", return_value=_fake_response(400)):
            with pytest.raises(RuntimeError, match="prep submit failed"):
                _orch.submit_prep("key123", "/data/comic.cbz")


# ---------------------------------------------------------------------------
# Tests submit_ocr
# ---------------------------------------------------------------------------

class TestSubmitOcr:
    """Tests de la fonction submit_ocr."""

    def test_ok_ne_leve_pas(self):
        """submit_ocr avec réponse 202 ne lève pas d'exception."""
        with patch("app.main.requests.post", return_value=_fake_response(202)):
            _orch.submit_ocr("key123", "/data/work/key123/raw.pdf")

    def test_erreur_leve_runtime(self):
        """submit_ocr avec réponse 500 lève RuntimeError."""
        with patch("app.main.requests.post", return_value=_fake_response(500)):
            with pytest.raises(RuntimeError, match="ocr submit failed"):
                _orch.submit_ocr("key123", "/data/raw.pdf")


# ---------------------------------------------------------------------------
# Tests poll_job
# ---------------------------------------------------------------------------

class TestPollJob:
    """Tests de la fonction poll_job."""

    def test_ok_retourne_json(self):
        """poll_job retourne le JSON d'état si réponse 200."""
        fake = _fake_response(200, {"state": "DONE", "artifacts": {"finalPdf": "/out/x.pdf"}})
        with patch("app.main.requests.get", return_value=fake):
            result = _orch.poll_job("http://mock-prep:8080", "key123")

        assert result["state"] == "DONE"

    def test_erreur_404_leve_runtime(self):
        """poll_job avec code 404 lève RuntimeError."""
        with patch("app.main.requests.get", return_value=_fake_response(404)):
            with pytest.raises(RuntimeError, match="job status failed"):
                _orch.poll_job("http://mock-prep:8080", "key123")

    def test_erreur_500_leve_runtime(self):
        """poll_job avec code 500 lève RuntimeError."""
        with patch("app.main.requests.get", return_value=_fake_response(500)):
            with pytest.raises(RuntimeError, match="job status failed"):
                _orch.poll_job("http://mock-ocr:8080", "key456")


# ---------------------------------------------------------------------------
# Tests check_duplicate_decisions
# ---------------------------------------------------------------------------

class TestCheckDuplicateDecisions:
    """Tests de check_duplicate_decisions — toutes les branches d'action."""

    def _setup(self, tmp_path, monkeypatch):
        _setup_dirs(tmp_path)
        _patch_dirs(tmp_path, monkeypatch)

    def _make_held_file(self, tmp_path, job_key, action, cbz_name="comic.cbz"):
        """Crée un dossier hold avec un CBZ et une decision.json."""
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True, exist_ok=True)
        cbz = hold_dir / cbz_name
        cbz.write_bytes(b"PK\x03\x04fake")
        atomic_write_json(
            str(hold_dir / "decision.json"),
            {"action": action, "nonce": "abc12345"},
        )
        atomic_write_json(
            str(hold_dir / "status.json"),
            {"jobKey": job_key, "state": "DUPLICATE_PENDING", "updatedAt": now_iso()},
        )
        return hold_dir, str(cbz)

    def test_use_existing_result_archive_cbz(self, tmp_path, monkeypatch):
        """USE_EXISTING_RESULT archive le fichier entrant et copie le PDF existant."""
        self._setup(tmp_path, monkeypatch)
        job_key = "jk1__use"
        out_pdf = tmp_path / "out" / "existing.pdf"
        out_pdf.write_bytes(b"%PDF-existing")

        hold_dir, cbz_path = self._make_held_file(tmp_path, job_key, "USE_EXISTING_RESULT")
        atomic_write_json(
            str(tmp_path / "reports" / "duplicates" / f"{job_key}.json"),
            {"jobKey": job_key},
        )
        index = {"jobs": {job_key: {
            "jobKey": job_key, "state": "DONE", "outPdf": str(out_pdf),
        }}}
        index_path = str(tmp_path / "index" / "jobs.json")
        atomic_write_json(index_path, index)

        _orch.check_duplicate_decisions(index, index_path)

        archive_files = list((tmp_path / "archive").glob("*.cbz"))
        assert len(archive_files) == 1, "Le CBZ doit être archivé"

    def test_discard_supprime_fichier(self, tmp_path, monkeypatch):
        """DISCARD supprime le fichier entrant."""
        self._setup(tmp_path, monkeypatch)
        job_key = "jk2__disc"
        hold_dir, cbz_path = self._make_held_file(tmp_path, job_key, "DISCARD", "discard.cbz")
        atomic_write_json(
            str(tmp_path / "reports" / "duplicates" / f"{job_key}.json"),
            {"jobKey": job_key},
        )
        index = {"jobs": {job_key: {"jobKey": job_key, "state": "DONE", "outPdf": None}}}
        index_path = str(tmp_path / "index" / "jobs.json")
        atomic_write_json(index_path, index)

        _orch.check_duplicate_decisions(index, index_path)

        assert not (hold_dir / "discard.cbz").exists(), "CBZ doit avoir été supprimé"

    def test_force_reprocess_deplace_vers_in(self, tmp_path, monkeypatch):
        """FORCE_REPROCESS déplace le fichier vers IN_DIR avec suffixe __force-."""
        self._setup(tmp_path, monkeypatch)
        job_key = "jk3__force"
        hold_dir, cbz_path = self._make_held_file(tmp_path, job_key, "FORCE_REPROCESS", "force.cbz")
        atomic_write_json(
            str(tmp_path / "reports" / "duplicates" / f"{job_key}.json"),
            {"jobKey": job_key},
        )
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")
        atomic_write_json(index_path, index)

        _orch.check_duplicate_decisions(index, index_path)

        in_dir = tmp_path / "in"
        force_files = list(in_dir.glob("*__force-*.cbz"))
        assert len(force_files) == 1, "CBZ doit être dans IN_DIR avec suffixe __force-"

    def test_pas_de_decision_json_ignoree(self, tmp_path, monkeypatch):
        """Sans decision.json dans le hold, le dossier est ignoré silencieusement."""
        self._setup(tmp_path, monkeypatch)
        job_key = "jk4__nodec"
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True, exist_ok=True)
        (hold_dir / "comic.cbz").write_bytes(b"PK\x03\x04")
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")

        _orch.check_duplicate_decisions(index, index_path)

        assert (hold_dir / "comic.cbz").exists(), "CBZ doit rester intact"

    def test_hold_vide_pas_dexception(self, tmp_path, monkeypatch):
        """check_duplicate_decisions avec hold/ vide ne lève pas d'exception."""
        self._setup(tmp_path, monkeypatch)
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")

        _orch.check_duplicate_decisions(index, index_path)


# ---------------------------------------------------------------------------
# Tests process_loop
# ---------------------------------------------------------------------------

class TestProcessLoop:
    """Tests de la boucle process_loop — stoppée proprement via StopIteration."""

    def _setup(self, tmp_path, monkeypatch):
        _setup_dirs(tmp_path)
        _patch_dirs(tmp_path, monkeypatch)

    def test_appelle_process_tick(self, tmp_path, monkeypatch):
        """process_loop appelle process_tick au moins une fois avant de s'arrêter."""
        self._setup(tmp_path, monkeypatch)
        tick_calls = []

        def fake_tick(in_flight, index, index_path, profile, config):
            tick_calls.append(1)
            if len(tick_calls) >= 2:
                raise StopIteration

        with patch("app.main.process_tick", side_effect=fake_tick), \
             patch("app.main.get_service_info", return_value={"versions": {}}), \
             patch("app.main.start_http_server"), \
             patch("app.main.time.sleep"), \
             pytest.raises(StopIteration):
            _orch.process_loop()

        assert len(tick_calls) >= 2

    def test_appelle_ensure_layout_au_demarrage(self, tmp_path, monkeypatch):
        """process_loop appelle ensure_layout dès le démarrage."""
        self._setup(tmp_path, monkeypatch)
        layout_calls = []

        def fake_ensure_layout():
            layout_calls.append(1)

        def fake_tick(*args, **kwargs):
            raise StopIteration

        with patch("app.main.ensure_layout", side_effect=fake_ensure_layout), \
             patch("app.main.process_tick", side_effect=fake_tick), \
             patch("app.main.get_service_info", return_value={"versions": {}}), \
             patch("app.main.start_http_server"), \
             patch("app.main.time.sleep"), \
             pytest.raises(StopIteration):
            _orch.process_loop()

        assert len(layout_calls) >= 1

    def test_charge_index_existant(self, tmp_path, monkeypatch):
        """process_loop charge l'index JSON existant et le passe à process_tick."""
        self._setup(tmp_path, monkeypatch)
        index_path = str(tmp_path / "index" / "jobs.json")
        atomic_write_json(index_path, {"jobs": {"existing_key": {"state": "DONE"}}})

        captured = []

        def fake_tick(in_flight, index, idx_path, profile, config):
            captured.append(dict(index))
            raise StopIteration

        with patch("app.main.process_tick", side_effect=fake_tick), \
             patch("app.main.get_service_info", return_value={"versions": {}}), \
             patch("app.main.start_http_server"), \
             patch("app.main.time.sleep"), \
             pytest.raises(StopIteration):
            _orch.process_loop()

        assert "existing_key" in captured[0]["jobs"]

    def test_appelle_get_service_info(self, tmp_path, monkeypatch):
        """process_loop appelle get_service_info pour prep et ocr."""
        self._setup(tmp_path, monkeypatch)
        service_urls = []

        def fake_get_info(url):
            service_urls.append(url)
            return {"versions": {}}

        def fake_tick(*args, **kwargs):
            raise StopIteration

        with patch("app.main.get_service_info", side_effect=fake_get_info), \
             patch("app.main.process_tick", side_effect=fake_tick), \
             patch("app.main.start_http_server"), \
             patch("app.main.time.sleep"), \
             pytest.raises(StopIteration):
            _orch.process_loop()

        assert len(service_urls) == 2  # prep + ocr

    def test_config_passee_a_process_tick(self, tmp_path, monkeypatch):
        """process_loop passe une config complète à process_tick."""
        self._setup(tmp_path, monkeypatch)
        captured_config = []

        def fake_tick(in_flight, index, idx_path, profile, config):
            captured_config.append(config)
            raise StopIteration

        with patch("app.main.process_tick", side_effect=fake_tick), \
             patch("app.main.get_service_info", return_value={"versions": {}}), \
             patch("app.main.start_http_server"), \
             patch("app.main.time.sleep"), \
             pytest.raises(StopIteration):
            _orch.process_loop()

        cfg = captured_config[0]
        assert "prep_url" in cfg
        assert "ocr_url" in cfg
        assert "max_jobs_in_flight" in cfg
        assert "metrics" in cfg

