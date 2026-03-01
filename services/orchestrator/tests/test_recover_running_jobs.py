"""
Tests de bootstrap recover_running_jobs (services/orchestrator/app/main.py).

Vérifie :
- safe_load_json : absent, JSON invalide, JSON valide
- Cas 1 : PREP_RUNNING + state.json valide (attemptPrep=2) => in_flight reconstruit
- Cas 2 : OCR_RUNNING  + state.json absent => fallback attempt=1, inputPath fallback
- Cas 3 : state.json corrompu => fallback attempt=1, pas d'exception
- Cas 4 : attempt >= max => job passe ERROR (message max_attempts_after_restart)
- Cas 5 : dossier work/<jobKey> absent => pas d'exception, fallback correct

Aucun outil externe requis. HTTP entièrement absent (pas de soumission).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.core import safe_load_json


# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

def _make_config(tmp_path) -> dict:
    """Construit un dict de config minimal pointant vers tmp_path."""
    return {
        "prep_url": "http://mock-prep:8080",
        "ocr_url": "http://mock-ocr:8080",
        "work_dir": str(tmp_path / "work"),
        "max_jobs_in_flight": 3,
        "prep_concurrency": 2,
        "ocr_concurrency": 1,
        "max_attempts_prep": 3,
        "max_attempts_ocr": 3,
        "job_timeout_s": 600,
        "index_dir": str(tmp_path / "index"),
        "metrics": {
            "done": 0,
            "error": 0,
            "running": 0,
            "queued": 0,
            "disk_error": 0,
            "pdf_invalid": 0,
            "input_rejected_size": 0,
            "input_rejected_signature": 0,
            "updatedAt": "",
        },
        "keep_work_dir_days": 7,
        "min_pdf_size_bytes": 1024,
        "disk_free_factor": 2.0,
        "max_input_size_mb": 500,
    }


def _setup_dirs(tmp_path):
    """Crée l'arborescence de données minimale."""
    for d in [
        "in", "out", "work", "error", "archive",
        "hold/duplicates", "reports/duplicates", "index",
    ]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)


def _patch_orch(monkeypatch, orch, tmp_path):
    """Patch tous les répertoires globaux de l'orchestrateur vers tmp_path."""
    monkeypatch.setattr(orch, "IN_DIR", str(tmp_path / "in"))
    monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))
    monkeypatch.setattr(orch, "OUT_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(orch, "ERROR_DIR", str(tmp_path / "error"))
    monkeypatch.setattr(orch, "ARCHIVE_DIR", str(tmp_path / "archive"))
    monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
    monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
    monkeypatch.setattr(orch, "INDEX_DIR", str(tmp_path / "index"))


def _write_index(tmp_path, index: dict) -> str:
    """Écrit l'index dans tmp_path/index/jobs.json et retourne le chemin."""
    index_path = str(tmp_path / "index" / "jobs.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f)
    return index_path


def _make_index_entry(job_key: str, state: str, input_name: str) -> dict:
    """Retourne une entrée d'index minimale."""
    return {
        "jobKey": job_key,
        "state": state,
        "inputName": input_name,
        "outPdf": None,
        "updatedAt": "2026-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# TestSafeLoadJson
# ---------------------------------------------------------------------------

class TestSafeLoadJson:
    """Tests unitaires de safe_load_json (app/core.py)."""

    def test_fichier_absent_retourne_false_absent(self, tmp_path):
        """Un fichier inexistant retourne (False, 'absent')."""
        ok, err = safe_load_json(str(tmp_path / "nope.json"))
        assert ok is False
        assert err == "absent"

    def test_json_invalide_retourne_false_json_corrupt(self, tmp_path):
        """Un JSON syntaxiquement invalide retourne (False, 'json_corrupt:...')."""
        p = tmp_path / "bad.json"
        p.write_text("{ invalide !!! pas du JSON", encoding="utf-8")
        ok, err = safe_load_json(str(p))
        assert ok is False
        assert "json_corrupt" in str(err)

    def test_json_valide_retourne_true_et_dict(self, tmp_path):
        """Un JSON valide retourne (True, dict) avec les bonnes valeurs."""
        p = tmp_path / "ok.json"
        p.write_text(
            json.dumps({"state": "PREP_RUNNING", "attemptPrep": 2}),
            encoding="utf-8",
        )
        ok, data = safe_load_json(str(p))
        assert ok is True
        assert isinstance(data, dict)
        assert data["attemptPrep"] == 2

    def test_fichier_vide_retourne_false(self, tmp_path):
        """Un fichier JSON vide (0 octet) retourne (False, ...) sans lever."""
        p = tmp_path / "empty.json"
        p.write_bytes(b"")
        ok, err = safe_load_json(str(p))
        assert ok is False

    def test_ne_leve_jamais_exception(self, tmp_path):
        """safe_load_json ne propage aucune exception, quelle que soit l'entrée."""
        for content in [b"", b"null", b"{ bad", b"\xff\xfe"]:
            p = tmp_path / "x.json"
            p.write_bytes(content)
            try:
                safe_load_json(str(p))
            except Exception as exc:
                pytest.fail(f"safe_load_json a levé une exception inattendue : {exc}")


# ---------------------------------------------------------------------------
# TestRecoverRunningJobs
# ---------------------------------------------------------------------------

class TestRecoverRunningJobs:
    """Tests de recover_running_jobs dans app/main.py."""

    def _get_orch(self, monkeypatch, tmp_path):
        import app.main as orch
        _setup_dirs(tmp_path)
        _patch_orch(monkeypatch, orch, tmp_path)
        return orch

    # ------------------------------------------------------------------
    # Cas 1 — PREP_RUNNING + state.json valide avec attemptPrep=2
    # ------------------------------------------------------------------

    def test_cas1_prep_running_state_valide_reconstruit_in_flight(self, tmp_path, monkeypatch):
        """PREP_RUNNING + state.json valide (attemptPrep=2, inputPath réel) =>
        in_flight reconstruit correctement avec stage=PREP_RETRY."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "aabbccdd__11223344"
        input_name = "comic.cbz"
        input_path = str(tmp_path / "work" / job_key / input_name)

        # Créer work/<job_key>/state.json valide
        jdir = tmp_path / "work" / job_key
        jdir.mkdir(parents=True)
        state = {
            "jobKey": job_key,
            "state": "PREP_RUNNING",
            "attemptPrep": 2,
            "attemptOcr": 0,
            "input": {"name": input_name, "path": input_path},
        }
        (jdir / "state.json").write_text(json.dumps(state), encoding="utf-8")

        index = {"jobs": {job_key: _make_index_entry(job_key, "PREP_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key in in_flight, "Le job doit être dans in_flight"
        meta = in_flight[job_key]
        assert meta["stage"] == "PREP_RETRY"
        assert meta["attemptPrep"] == 2
        assert meta["attemptOcr"] == 0
        assert meta["inputName"] == input_name
        assert meta["inputPath"] == input_path

    # ------------------------------------------------------------------
    # Cas 2 — OCR_RUNNING + state.json absent => fallback
    # ------------------------------------------------------------------

    def test_cas2_ocr_running_state_absent_fallback_attempt1(self, tmp_path, monkeypatch):
        """OCR_RUNNING + state.json absent => attemptOcr=1, inputPath = fallback work/<jk>/<name>."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "deadbeef__cafebabe"
        input_name = "bd.cbz"

        # Créer work/<job_key>/ mais SANS state.json
        (tmp_path / "work" / job_key).mkdir(parents=True)

        index = {"jobs": {job_key: _make_index_entry(job_key, "OCR_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key in in_flight
        meta = in_flight[job_key]
        assert meta["stage"] == "OCR_RETRY"
        assert meta["attemptOcr"] == 1
        assert meta["attemptPrep"] == 0
        expected_fallback = str(tmp_path / "work" / job_key / input_name)
        assert meta["inputPath"] == expected_fallback

    # ------------------------------------------------------------------
    # Cas 3 — state.json corrompu => fallback, sans crash
    # ------------------------------------------------------------------

    def test_cas3_state_corrompu_fallback_sans_crash(self, tmp_path, monkeypatch):
        """state.json corrompu => fallback attempt=1, pas d'exception, job requeue."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "badc0de__000000ff"
        input_name = "manga.cbz"

        jdir = tmp_path / "work" / job_key
        jdir.mkdir(parents=True)
        (jdir / "state.json").write_text("{ PAS DU JSON VALIDE !!!", encoding="utf-8")

        index = {"jobs": {job_key: _make_index_entry(job_key, "PREP_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        # Ne doit jamais lever d'exception
        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key in in_flight, "Le job doit quand même être requeue après state corrompu"
        meta = in_flight[job_key]
        assert meta["stage"] == "PREP_RETRY"
        assert meta["attemptPrep"] == 1

    # ------------------------------------------------------------------
    # Cas 4 — attempt >= max => passe ERROR, absent de in_flight
    # ------------------------------------------------------------------

    def test_cas4_max_attempts_prep_passe_en_error(self, tmp_path, monkeypatch):
        """attemptPrep=3 >= max_attempts_prep=3 => ERROR_PREP, job absent de in_flight."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "ffffffff__eeeeeeee"
        input_name = "comic.cbz"

        jdir = tmp_path / "work" / job_key
        jdir.mkdir(parents=True)
        state = {
            "jobKey": job_key,
            "state": "PREP_RUNNING",
            "attemptPrep": 3,   # = max_attempts_prep
            "attemptOcr": 0,
            "input": {"name": input_name, "path": str(jdir / input_name)},
        }
        (jdir / "state.json").write_text(json.dumps(state), encoding="utf-8")

        index = {"jobs": {job_key: _make_index_entry(job_key, "PREP_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)  # max_attempts_prep=3
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key not in in_flight, "Job à max attempts ne doit pas être requeue"
        assert index["jobs"][job_key]["state"] == "ERROR_PREP"

    def test_cas4_max_attempts_ocr_passe_en_error(self, tmp_path, monkeypatch):
        """attemptOcr=3 >= max_attempts_ocr=3 => ERROR_OCR, job absent de in_flight."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "11111111__22222222"
        input_name = "vol2.cbz"

        jdir = tmp_path / "work" / job_key
        jdir.mkdir(parents=True)
        state = {
            "jobKey": job_key,
            "state": "OCR_RUNNING",
            "attemptPrep": 1,
            "attemptOcr": 3,   # = max_attempts_ocr
            "rawPdf": str(jdir / "raw.pdf"),
            "input": {"name": input_name, "path": str(jdir / input_name)},
        }
        (jdir / "state.json").write_text(json.dumps(state), encoding="utf-8")

        index = {"jobs": {job_key: _make_index_entry(job_key, "OCR_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key not in in_flight
        assert index["jobs"][job_key]["state"] == "ERROR_OCR"

    # ------------------------------------------------------------------
    # Cas 5 — dossier work/<jobKey> absent => pas d'exception
    # ------------------------------------------------------------------

    def test_cas5_workdir_absent_pas_exception_fallback(self, tmp_path, monkeypatch):
        """work/<jobKey>/ inexistant => safe_load_json retourne absent, fallback utilisé, pas de crash."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "00000000__11111111"
        input_name = "no_workdir.cbz"
        # NE PAS créer work/<job_key>/

        index = {"jobs": {job_key: _make_index_entry(job_key, "PREP_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key in in_flight
        meta = in_flight[job_key]
        assert meta["stage"] == "PREP_RETRY"
        assert meta["attemptPrep"] == 1
        assert meta["inputPath"] == str(tmp_path / "work" / job_key / input_name)

    # ------------------------------------------------------------------
    # Cas 6 — Jobs en état DONE / DISCOVERED ignorés
    # ------------------------------------------------------------------

    def test_jobs_non_running_ignores(self, tmp_path, monkeypatch):
        """Les jobs en état DONE, DISCOVERED, ERROR ne sont pas touchés."""
        orch = self._get_orch(monkeypatch, tmp_path)

        index = {
            "jobs": {
                "done__key": _make_index_entry("done__key", "DONE", "ok.cbz"),
                "disc__key": _make_index_entry("disc__key", "DISCOVERED", "disc.cbz"),
                "err__key":  _make_index_entry("err__key",  "ERROR_PREP", "err.cbz"),
            }
        }
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert len(in_flight) == 0, "Aucun job non-RUNNING ne doit être dans in_flight"

    # ------------------------------------------------------------------
    # Cas 7 — OCR_RUNNING avec state.json valide : rawPdf transmis
    # ------------------------------------------------------------------

    def test_ocr_running_rawpdf_transmis(self, tmp_path, monkeypatch):
        """OCR_RUNNING + state.json valide => rawPdf présent dans meta in_flight."""
        orch = self._get_orch(monkeypatch, tmp_path)

        job_key = "abcdef__012345"
        input_name = "tome3.cbz"
        raw_pdf_path = str(tmp_path / "work" / job_key / "raw.pdf")
        input_path = str(tmp_path / "work" / job_key / input_name)

        jdir = tmp_path / "work" / job_key
        jdir.mkdir(parents=True)
        state = {
            "jobKey": job_key,
            "state": "OCR_RUNNING",
            "attemptPrep": 1,
            "attemptOcr": 2,
            "rawPdf": raw_pdf_path,
            "input": {"name": input_name, "path": input_path},
        }
        (jdir / "state.json").write_text(json.dumps(state), encoding="utf-8")

        index = {"jobs": {job_key: _make_index_entry(job_key, "OCR_RUNNING", input_name)}}
        index_path = _write_index(tmp_path, index)
        config = _make_config(tmp_path)
        in_flight: dict = {}

        orch.recover_running_jobs(index, index_path, in_flight, config)

        assert job_key in in_flight
        meta = in_flight[job_key]
        assert meta["stage"] == "OCR_RETRY"
        assert meta["attemptOcr"] == 2
        assert meta.get("rawPdf") == raw_pdf_path

