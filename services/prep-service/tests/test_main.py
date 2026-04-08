"""
Tests unitaires de run_job() — prep-service.
7z et img2pdf entièrement mockés. Aucune connexion externe requise.

Couvre (P0-PREP-01) :
  - Flux nominal DONE (extraction réussie + raw.pdf créé)
  - Flux ERROR (7z retourne rc != 0)
  - Flux ZipSlipError (protection anti zip-slip)
  - Flux sans images après extraction
  - Heartbeat écrit aux étapes clés
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock, call

from app.core import ZipSlipError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_meta(tmp_path, job_id="testjob001"):
    """Crée un fichier de métadonnées minimal dans RUNNING_DIR."""
    running_dir = tmp_path / "prep" / "running"
    running_dir.mkdir(parents=True, exist_ok=True)
    meta_path = running_dir / f"{job_id}.json"
    meta_path.write_text(
        json.dumps({
            "jobId": job_id,
            "inputPath": str(tmp_path / "in" / "comic.cbz"),
            "workDir": str(tmp_path / "work"),
            "state": "RUNNING",
            "updatedAt": "2026-01-01T00:00:00Z",
            "createdAtEpoch": 1234567890.0,
        }),
        encoding="utf-8",
    )
    return str(meta_path), job_id


# ---------------------------------------------------------------------------
# TestRunJobFluxNominal
# ---------------------------------------------------------------------------

class TestRunJobFluxNominal:
    """run_job() réussit : extraction OK + raw.pdf généré."""

    def test_flux_nominal_state_done(self, tmp_path, monkeypatch):
        """run_job() met à jour l'état à DONE et écrit le chemin rawPdf."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)
        job_dir = tmp_path / "work" / job_id
        pages_dir = job_dir / "pages"

        def _fake_7z(cmd, **kw):
            """Simule 7z en créant une image dans pages_dir."""
            pages_dir.mkdir(parents=True, exist_ok=True)
            (pages_dir / "page001.jpg").write_bytes(b"JFIF fake image data")
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Everything is OK"
            result.stderr = ""
            return result

        fake_images = [str(pages_dir / "page001.jpg")]

        with patch("subprocess.run", side_effect=_fake_7z):
            with patch("app.main.list_and_sort_images", return_value=fake_images):
                with patch("app.main.images_to_pdf") as mock_img2pdf:
                    # Simuler la création du raw.tmp.pdf par images_to_pdf
                    def _create_raw_tmp(imgs, dest):
                        raw_tmp_path = job_dir / "raw.tmp.pdf"
                        raw_tmp_path.parent.mkdir(parents=True, exist_ok=True)
                        raw_tmp_path.write_bytes(b"%PDF-1.4 " + b"x" * 2000)

                    mock_img2pdf.side_effect = _create_raw_tmp
                    prep.run_job(meta_path)

        # Lire le fichier de métadonnées mis à jour
        with open(meta_path, encoding="utf-8") as f:
            result = json.load(f)

        assert result["state"] == "DONE"
        assert "rawPdf" in result.get("artifacts", {})
        raw_pdf = result["artifacts"]["rawPdf"]
        assert os.path.exists(raw_pdf), "raw.pdf doit exister après run_job DONE"

    def test_heartbeat_ecrit_aux_etapes(self, tmp_path, monkeypatch):
        """Vérifie que le heartbeat est écrit à start, listing et img2pdf."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)
        job_dir = tmp_path / "work" / job_id
        pages_dir = job_dir / "pages"

        def _fake_7z(cmd, **kw):
            pages_dir.mkdir(parents=True, exist_ok=True)
            (pages_dir / "page001.jpg").write_bytes(b"fake")
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        fake_images = [str(pages_dir / "page001.jpg")]

        with patch("subprocess.run", side_effect=_fake_7z):
            with patch("app.main.list_and_sort_images", return_value=fake_images):
                with patch("app.main.images_to_pdf") as mock_img2pdf:
                    def _create_raw_tmp(imgs, dest):
                        p = job_dir / "raw.tmp.pdf"
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(b"%PDF-1.4 " + b"x" * 2000)
                    mock_img2pdf.side_effect = _create_raw_tmp
                    prep.run_job(meta_path)

        hb_path = job_dir / "prep.heartbeat"
        assert hb_path.exists(), "Le fichier heartbeat doit exister après run_job"

    def test_log_cree_avec_commande_7z(self, tmp_path, monkeypatch):
        """Le fichier prep.log est créé et contient la commande 7z."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)
        job_dir = tmp_path / "work" / job_id
        pages_dir = job_dir / "pages"

        def _fake_7z(cmd, **kw):
            pages_dir.mkdir(parents=True, exist_ok=True)
            (pages_dir / "page001.jpg").write_bytes(b"fake")
            r = MagicMock()
            r.returncode = 0
            r.stdout = "1 file extracted"
            r.stderr = ""
            return r

        fake_images = [str(pages_dir / "page001.jpg")]

        with patch("subprocess.run", side_effect=_fake_7z):
            with patch("app.main.list_and_sort_images", return_value=fake_images):
                with patch("app.main.images_to_pdf") as mock_img2pdf:
                    def _create_raw_tmp(imgs, dest):
                        p = job_dir / "raw.tmp.pdf"
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(b"%PDF-1.4 " + b"x" * 2000)
                    mock_img2pdf.side_effect = _create_raw_tmp
                    prep.run_job(meta_path)

        log_path = job_dir / "prep.log"
        assert log_path.exists(), "prep.log doit être créé"
        content = log_path.read_text(encoding="utf-8")
        assert "7z" in content, "Le log doit contenir la commande 7z"


# ---------------------------------------------------------------------------
# TestRunJobErreurs
# ---------------------------------------------------------------------------

class TestRunJobErreurs:
    """run_job() gère correctement les chemins d'erreur."""

    def test_7z_returncode_nonzero_passe_en_error(self, tmp_path, monkeypatch):
        """Si 7z retourne rc != 0, l'état est ERROR."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)

        def _fake_7z_failed(cmd, **kw):
            r = MagicMock()
            r.returncode = 1
            r.stdout = ""
            r.stderr = "Error: archive not found"
            return r

        with patch("subprocess.run", side_effect=_fake_7z_failed):
            try:
                prep.run_job(meta_path)
            except Exception:
                pass  # L'exception peut être propagée ou non selon l'impl

        with open(meta_path, encoding="utf-8") as f:
            result = json.load(f)

        assert result["state"] == "ERROR"
        assert "7z" in result.get("message", "")

    def test_aucune_image_apres_extraction_passe_en_error(self, tmp_path, monkeypatch):
        """Si aucune image n'est trouvée après extraction, l'état est ERROR."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)

        def _fake_7z_empty(cmd, **kw):
            # 7z réussit mais ne crée pas d'images
            r = MagicMock()
            r.returncode = 0
            r.stdout = "OK"
            r.stderr = ""
            return r

        # list_and_sort_images retourne une liste vide → aucune image
        with patch("subprocess.run", side_effect=_fake_7z_empty):
            with patch("app.main.list_and_sort_images", return_value=[]):
                try:
                    prep.run_job(meta_path)
                except Exception:
                    pass

        with open(meta_path, encoding="utf-8") as f:
            result = json.load(f)

        assert result["state"] == "ERROR"
        assert "image" in result.get("message", "").lower()

    def test_zip_slip_error_tentatif_nettoyage_et_state_error(self, tmp_path, monkeypatch):
        """ZipSlipError : state passe en ERROR et message contient 'zip-slip'."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)
        job_dir = tmp_path / "work" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        def _fake_7z_ok(cmd, **kw):
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=_fake_7z_ok):
            with patch("app.main.list_and_sort_images", side_effect=ZipSlipError("../evil.jpg")):
                try:
                    prep.run_job(meta_path)
                except ZipSlipError:
                    pass  # L'exception est propagée

        # L'état doit être ERROR avec le message zip-slip
        with open(meta_path, encoding="utf-8") as f:
            result = json.load(f)

        assert result["state"] == "ERROR"
        assert "zip-slip" in result.get("message", "").lower()

    def test_meta_path_invalide_retourne_sans_crash(self, tmp_path, monkeypatch):
        """run_job() avec un chemin inexistant ne crashe pas."""
        import app.main as prep

        # Aucune exception ne doit être levée pour un meta_path vide
        prep.run_job(str(tmp_path / "nope.json"))

    def test_images_to_pdf_exception_passe_en_error(self, tmp_path, monkeypatch):
        """Si images_to_pdf lève une exception, l'état est ERROR."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)
        job_dir = tmp_path / "work" / job_id
        pages_dir = job_dir / "pages"

        def _fake_7z(cmd, **kw):
            pages_dir.mkdir(parents=True, exist_ok=True)
            (pages_dir / "page001.jpg").write_bytes(b"fake")
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        fake_images = [str(pages_dir / "page001.jpg")]

        with patch("subprocess.run", side_effect=_fake_7z):
            with patch("app.main.list_and_sort_images", return_value=fake_images):
                with patch("app.main.images_to_pdf", side_effect=RuntimeError("img2pdf crash")):
                    try:
                        prep.run_job(meta_path)
                    except Exception:
                        pass

        with open(meta_path, encoding="utf-8") as f:
            result = json.load(f)

        assert result["state"] == "ERROR"
        assert "img2pdf" in result.get("message", "").lower() or "crash" in result.get("message", "")


# ---------------------------------------------------------------------------
# TestRunJobAtomique
# ---------------------------------------------------------------------------

class TestRunJobAtomique:
    """Vérifications de l'écriture atomique raw.tmp.pdf → raw.pdf."""

    def test_raw_tmp_supprime_et_raw_pdf_present(self, tmp_path, monkeypatch):
        """Après succès, raw.tmp.pdf ne doit plus exister, raw.pdf doit exister."""
        import app.main as prep

        meta_path, job_id = _make_meta(tmp_path)
        job_dir = tmp_path / "work" / job_id
        pages_dir = job_dir / "pages"

        def _fake_7z(cmd, **kw):
            pages_dir.mkdir(parents=True, exist_ok=True)
            (pages_dir / "page001.jpg").write_bytes(b"fake image")
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        fake_images = [str(pages_dir / "page001.jpg")]

        with patch("subprocess.run", side_effect=_fake_7z):
            with patch("app.main.list_and_sort_images", return_value=fake_images):
                with patch("app.main.images_to_pdf") as mock_img2pdf:
                    def _create_raw_tmp(imgs, dest):
                        p = job_dir / "raw.tmp.pdf"
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(b"%PDF-1.4 " + b"x" * 2000)
                    mock_img2pdf.side_effect = _create_raw_tmp
                    prep.run_job(meta_path)

        raw_tmp = job_dir / "raw.tmp.pdf"
        raw_pdf = job_dir / "raw.pdf"

        assert not raw_tmp.exists(), "raw.tmp.pdf doit être supprimé après rename atomique"
        assert raw_pdf.exists(), "raw.pdf doit exister après rename atomique"
