"""
Tests unitaires de l'orchestrateur :
doublons, heartbeat-check (check_stale_jobs).
HTTP entièrement mocké.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock


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
        "metrics": {"done": 0, "error": 0, "running": 0, "queued": 0, "updatedAt": ""},
    }


def _setup_dirs(tmp_path):
    """Crée l'arborescence de données minimale."""
    dirs = [
        "in", "out", "work", "error", "archive",
        "hold/duplicates", "reports/duplicates", "index",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Doublons
# ---------------------------------------------------------------------------

class TestDoublons:
    """Vérifications de la détection et du traitement des doublons."""

    def test_doublon_place_dans_hold_et_rapport_cree(self, tmp_path, monkeypatch):
        """Un fichier avec un jobKey déjà connu est mis dans hold/duplicates
        et un rapport est créé dans reports/duplicates."""
        import app.main as orch

        _setup_dirs(tmp_path)

        # Patch des répertoires globaux de l'orchestrateur
        monkeypatch.setattr(orch, "IN_DIR", str(tmp_path / "in"))
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))
        monkeypatch.setattr(orch, "OUT_DIR", str(tmp_path / "out"))
        monkeypatch.setattr(orch, "ERROR_DIR", str(tmp_path / "error"))
        monkeypatch.setattr(orch, "ARCHIVE_DIR", str(tmp_path / "archive"))
        monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
        monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
        monkeypatch.setattr(orch, "INDEX_DIR", str(tmp_path / "index"))

        job_key = "aabbccdd__11223344"
        # Index pré-rempli avec le même jobKey
        existing_entry = {"jobKey": job_key, "state": "DONE", "outPdf": "/out/result.pdf"}

        incoming_path = str(tmp_path / "incoming.cbz")
        with open(incoming_path, "wb") as f:
            f.write(b"fake comic content")

        orch.write_duplicate_report(job_key, incoming_path, existing_entry, {"ocr": {}, "prep": {}})

        # Vérification : le fichier est dans hold/duplicates/<jobKey>/
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        assert hold_dir.exists()
        held = list(hold_dir.glob("*__incoming.cbz"))
        assert len(held) == 1, "Le fichier entrant doit être dans hold"

        # Vérification : le rapport existe dans reports/duplicates/<jobKey>.json
        report_path = tmp_path / "reports" / "duplicates" / f"{job_key}.json"
        assert report_path.exists(), "Le rapport de doublon doit exister"

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert report["jobKey"] == job_key
        assert "incoming" in report
        assert "existing" in report
        assert "USE_EXISTING_RESULT" in report["actions"]

    def test_rapport_contient_champs_requis(self, tmp_path, monkeypatch):
        """Le rapport de doublon contient tous les champs attendus."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
        monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))

        incoming = str(tmp_path / "comic.cbz")
        with open(incoming, "wb") as f:
            f.write(b"x" * 100)

        job_key = "deadbeef__cafebabe"
        orch.write_duplicate_report(job_key, incoming, {"state": "DONE"}, {"ocr": {}})

        report_path = tmp_path / "reports" / "duplicates" / f"{job_key}.json"
        with open(report_path, "r", encoding="utf-8") as f:
            r = json.load(f)

        for champ in ["jobKey", "detectedAt", "incoming", "existing", "profile", "actions"]:
            assert champ in r, f"Champ manquant : {champ}"

        assert r["incoming"]["sizeBytes"] == 100


# ---------------------------------------------------------------------------
# check_stale_jobs
# ---------------------------------------------------------------------------

class TestCheckStaleJobs:
    """Vérifications de la détection de heartbeats périmés."""

    def test_prep_running_avec_heartbeat_vieux_bascule_en_retry(self, tmp_path, monkeypatch):
        """Un job PREP_RUNNING avec un heartbeat trop vieux bascule en PREP_RETRY."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "stalejob_prep_001"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        # Créer un heartbeat périmé (700 secondes)
        hb_path = job_dir / "prep.heartbeat"
        hb_path.write_text("old heartbeat\n")
        old_time = time.time() - 700
        os.utime(str(hb_path), (old_time, old_time))

        # Créer le state.json pour update_state
        state_path = job_dir / "state.json"
        state_path.write_text(json.dumps({"jobKey": job_key, "state": "PREP_RUNNING"}))

        in_flight = {
            job_key: {
                "stage": "PREP_RUNNING",
                "inputName": "test.cbz",
                "inputPath": str(tmp_path / "work" / job_key / "test.cbz"),
                "attemptPrep": 1,
                "attemptOcr": 0,
            }
        }

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "PREP_RETRY", \
            "Le job doit basculer en PREP_RETRY après timeout heartbeat"

    def test_prep_running_avec_heartbeat_recent_reste_running(self, tmp_path, monkeypatch):
        """Un job PREP_RUNNING avec un heartbeat récent reste en PREP_RUNNING."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "freshprepjob"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        hb_path = job_dir / "prep.heartbeat"
        hb_path.write_text("recent heartbeat\n")
        os.utime(str(hb_path), None)  # mtime = now

        state_path = job_dir / "state.json"
        state_path.write_text(json.dumps({"jobKey": job_key, "state": "PREP_RUNNING"}))

        in_flight = {
            job_key: {
                "stage": "PREP_RUNNING",
                "inputName": "test.cbz",
                "inputPath": "",
                "attemptPrep": 1,
                "attemptOcr": 0,
            }
        }

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "PREP_RUNNING", \
            "Le job doit rester en PREP_RUNNING si le heartbeat est récent"

    def test_ocr_running_avec_heartbeat_vieux_bascule_en_retry(self, tmp_path, monkeypatch):
        """Un job OCR_RUNNING avec un heartbeat trop vieux bascule en OCR_RETRY."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "stalejob_ocr_001"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        hb_path = job_dir / "ocr.heartbeat"
        hb_path.write_text("old ocr heartbeat\n")
        old_time = time.time() - 700
        os.utime(str(hb_path), (old_time, old_time))

        state_path = job_dir / "state.json"
        state_path.write_text(json.dumps({"jobKey": job_key, "state": "OCR_RUNNING"}))

        in_flight = {
            job_key: {
                "stage": "OCR_RUNNING",
                "inputName": "test.cbz",
                "inputPath": "",
                "attemptPrep": 1,
                "attemptOcr": 1,
                "rawPdf": str(job_dir / "raw.pdf"),
            }
        }

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "OCR_RETRY"

    def test_job_discovered_non_affecte(self, tmp_path, monkeypatch):
        """Un job en stage DISCOVERED n'est pas affecté par check_stale_jobs."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "discoveredjob"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        in_flight = {job_key: {"stage": "DISCOVERED", "attemptPrep": 0, "attemptOcr": 0}}

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "DISCOVERED"

