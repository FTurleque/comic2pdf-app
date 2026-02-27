"""
Tests unitaires du ocr-service — exécution de jobs (subprocess mocké).
Aucun outil externe requis.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _write_job_meta(path: str, data: dict):
    """Écrit un fichier de métadonnées JSON pour un job."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# run_job : cas OK
# ---------------------------------------------------------------------------

class TestRunJobOk:
    """Job OCR qui réussit : mock subprocess rc=0, final.pdf créé."""

    def test_state_done_apres_succes(self, tmp_path, mocker):
        """Après un run_job réussi, l'état du job est DONE."""
        import app.main as svc

        work_dir = str(tmp_path / "work")
        job_id = "testjob01"
        job_dir = os.path.join(work_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Créer raw.pdf factice
        raw_pdf = os.path.join(job_dir, "raw.pdf")
        with open(raw_pdf, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        meta_path = os.path.join(work_dir, f"{job_id}.json")
        _write_job_meta(meta_path, {
            "jobId": job_id,
            "rawPdfPath": raw_pdf,
            "workDir": work_dir,
            "lang": "fra+eng",
            "rotatePages": True,
            "deskew": True,
            "optimize": 1,
        })

        # Mock subprocess.run : rc=0 + crée final.tmp.pdf
        final_tmp = os.path.join(job_dir, "final.tmp.pdf")

        def fake_run(cmd, **kwargs):
            # Simuler la création du fichier de sortie par ocrmypdf
            with open(final_tmp, "wb") as f:
                f.write(b"%PDF-1.4 ocr output")
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
            return m

        mocker.patch("subprocess.run", side_effect=fake_run)

        svc.run_job(meta_path)

        meta = _read_json(meta_path)
        assert meta["state"] == "DONE"
        assert os.path.exists(os.path.join(job_dir, "final.pdf"))
        assert meta["artifacts"]["finalPdf"].endswith("final.pdf")

    def test_final_pdf_existe_apres_succes(self, tmp_path, mocker):
        """Après succès, final.pdf est bien créé (rename atomique depuis final.tmp.pdf)."""
        import app.main as svc

        work_dir = str(tmp_path / "work2")
        job_id = "testjob02"
        job_dir = os.path.join(work_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        raw_pdf = os.path.join(job_dir, "raw.pdf")
        with open(raw_pdf, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        meta_path = os.path.join(work_dir, f"{job_id}.json")
        _write_job_meta(meta_path, {
            "jobId": job_id,
            "rawPdfPath": raw_pdf,
            "workDir": work_dir,
        })

        final_tmp = os.path.join(job_dir, "final.tmp.pdf")

        def fake_run(cmd, **kwargs):
            with open(final_tmp, "wb") as f:
                f.write(b"%PDF-1.4 result")
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
            return m

        mocker.patch("subprocess.run", side_effect=fake_run)
        svc.run_job(meta_path)

        assert os.path.exists(os.path.join(job_dir, "final.pdf"))
        assert not os.path.exists(final_tmp), "final.tmp.pdf doit être supprimé après le rename"


# ---------------------------------------------------------------------------
# run_job : cas ERROR
# ---------------------------------------------------------------------------

class TestRunJobError:
    """Job OCR qui échoue : mock subprocess rc!=0."""

    def test_state_error_si_ocrmypdf_echoue(self, tmp_path, mocker):
        """Si ocrmypdf retourne rc!=0, l'état du job est ERROR."""
        import app.main as svc

        work_dir = str(tmp_path / "work_err")
        job_id = "errjob01"
        job_dir = os.path.join(work_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        raw_pdf = os.path.join(job_dir, "raw.pdf")
        with open(raw_pdf, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        meta_path = os.path.join(work_dir, f"{job_id}.json")
        _write_job_meta(meta_path, {
            "jobId": job_id,
            "rawPdfPath": raw_pdf,
            "workDir": work_dir,
        })

        def fake_run_fail(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 1
            m.stdout = ""
            m.stderr = "ocrmypdf error output\n"
            return m

        mocker.patch("subprocess.run", side_effect=fake_run_fail)

        with pytest.raises(RuntimeError):
            svc.run_job(meta_path)

        meta = _read_json(meta_path)
        assert meta["state"] == "ERROR"
        assert "message" in meta
        assert "ocrmypdf failed" in meta["message"]

    def test_message_erreur_present(self, tmp_path, mocker):
        """Le champ 'error' avec type et détail est présent en cas d'échec."""
        import app.main as svc

        work_dir = str(tmp_path / "work_err2")
        job_id = "errjob02"
        job_dir = os.path.join(work_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        raw_pdf = os.path.join(job_dir, "raw.pdf")
        with open(raw_pdf, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        meta_path = os.path.join(work_dir, f"{job_id}.json")
        _write_job_meta(meta_path, {
            "jobId": job_id,
            "rawPdfPath": raw_pdf,
            "workDir": work_dir,
        })

        mocker.patch("subprocess.run", return_value=MagicMock(
            returncode=2, stdout="", stderr="fatal error"
        ))

        with pytest.raises(RuntimeError):
            svc.run_job(meta_path)

        meta = _read_json(meta_path)
        assert "error" in meta
        assert meta["error"]["type"] == "RuntimeError"

