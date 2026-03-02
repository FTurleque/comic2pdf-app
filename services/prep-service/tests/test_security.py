"""
Tests de sécurité zip-slip pour le prep-service.

Couvre :
  - check_zip_slip : tous les chemins valides → OK
  - check_zip_slip : un chemin hors pages_dir → ZipSlipError
  - check_zip_slip : liste vide → OK (pas d'images, pas d'attaque)
  - list_and_sort_images intégré : simulation de fichier hors répertoire via mock
  - run_job : zip-slip → état ERROR + message "zip-slip" + workdir supprimé

Note : subprocess.run est toujours mocké, aucun outil système requis.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock

from app.core import check_zip_slip, ZipSlipError, list_and_sort_images
from app.utils import ensure_dir, atomic_write_json, now_iso


# ---------------------------------------------------------------------------
# Tests check_zip_slip
# ---------------------------------------------------------------------------

class TestCheckZipSlip:
    """Tests unitaires de check_zip_slip."""

    def test_tous_chemins_valides_retourne_liste(self, tmp_path):
        """Tous les chemins sous pages_dir → retourne la même liste."""
        pages = str(tmp_path / "pages")
        os.makedirs(pages)
        f1 = os.path.join(pages, "001.jpg")
        f2 = os.path.join(pages, "002.jpg")
        for f in [f1, f2]:
            open(f, "wb").close()
        result = check_zip_slip(pages, [f1, f2])
        assert result == [f1, f2]

    def test_chemin_hors_pages_leve_zipslip(self, tmp_path):
        """Un chemin hors de pages_dir lève ZipSlipError."""
        pages = str(tmp_path / "pages")
        os.makedirs(pages)
        safe_file = os.path.join(pages, "001.jpg")
        open(safe_file, "wb").close()
        # Fichier hors pages_dir
        unsafe_file = str(tmp_path / "danger.jpg")
        open(unsafe_file, "wb").close()
        with pytest.raises(ZipSlipError) as exc_info:
            check_zip_slip(pages, [safe_file, unsafe_file])
        assert "Zip-slip" in str(exc_info.value)

    def test_liste_vide_retourne_vide_sans_erreur(self, tmp_path):
        """Une liste vide ne lève pas d'erreur."""
        pages = str(tmp_path / "pages")
        os.makedirs(pages)
        result = check_zip_slip(pages, [])
        assert result == []

    def test_chemin_traversal_absolu_leve_zipslip(self, tmp_path):
        """Un chemin absolu hors pages_dir (simule extraction malveillante)."""
        pages = str(tmp_path / "pages")
        os.makedirs(pages)
        # Créer un fichier dans tmp_path/autre pour simuler un zip-slip
        autre = str(tmp_path / "autre")
        os.makedirs(autre)
        danger = os.path.join(autre, "malware.jpg")
        open(danger, "wb").close()
        with pytest.raises(ZipSlipError):
            check_zip_slip(pages, [danger])

    def test_sous_dossier_imbrique_valide(self, tmp_path):
        """Un sous-dossier imbriqué sous pages_dir est valide."""
        pages = str(tmp_path / "pages")
        nested = os.path.join(pages, "chapter1", "sub")
        os.makedirs(nested)
        f = os.path.join(nested, "001.jpg")
        open(f, "wb").close()
        result = check_zip_slip(pages, [f])
        assert result == [f]

    def test_message_erreur_contient_exemple_chemin(self, tmp_path):
        """Le message de ZipSlipError indique le chemin problématique."""
        pages = str(tmp_path / "pages")
        os.makedirs(pages)
        danger = str(tmp_path / "crontab.jpg")
        open(danger, "wb").close()
        with pytest.raises(ZipSlipError) as exc_info:
            check_zip_slip(pages, [danger])
        assert "crontab.jpg" in str(exc_info.value) or "Zip-slip" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tests list_and_sort_images intégré
# ---------------------------------------------------------------------------

class TestListAndSortImagesZipSlip:
    """Vérification que list_and_sort_images lève ZipSlipError si nécessaire."""

    def test_images_valides_pas_d_erreur(self, tmp_path):
        """Des images valides sous pages_dir ne lèvent pas d'erreur."""
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "001.jpg").write_bytes(b"\xff\xd8\xff")
        (pages / "002.jpg").write_bytes(b"\xff\xd8\xff")
        # Ne lève pas
        result = list_and_sort_images(str(pages))
        assert len(result) == 2

    def test_zip_slip_via_mock_filter_images(self, tmp_path):
        """Simule filter_images retournant un chemin hors pages_dir → ZipSlipError."""
        pages = str(tmp_path / "pages")
        os.makedirs(pages)
        danger = str(tmp_path / "danger.jpg")
        open(danger, "wb").close()

        with patch("app.core.filter_images", return_value=[danger]):
            with pytest.raises(ZipSlipError):
                list_and_sort_images(pages)


# ---------------------------------------------------------------------------
# Tests run_job avec zip-slip
# ---------------------------------------------------------------------------

class TestRunJobZipSlip:
    """Vérification que run_job gère ZipSlipError : ERROR + cleanup workdir."""

    def _make_job_file(self, tmp_path) -> str:
        """Crée un fichier de job minimal dans RUNNING_DIR."""
        running_dir = tmp_path / "running"
        running_dir.mkdir()
        job_dir = tmp_path / "work" / "test_job"
        job_dir.mkdir(parents=True)
        meta = {
            "jobId": "test_job",
            "inputPath": str(tmp_path / "input.cbz"),
            "workDir": str(tmp_path / "work"),
            "state": "QUEUED",
            "updatedAt": now_iso(),
        }
        meta_path = str(running_dir / "test_job.json")
        atomic_write_json(meta_path, meta)
        # Créer un faux fichier d'entrée
        (tmp_path / "input.cbz").write_bytes(b"PK\x03\x04")
        return meta_path

    def test_zip_slip_met_job_en_error(self, tmp_path):
        """run_job avec zip-slip → état ERROR avec message 'zip-slip'."""
        import app.main as prep_main

        meta_path = self._make_job_file(tmp_path)

        # Mocker subprocess.run (extraction 7z OK)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "ok"
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc):
            # Simuler un zip-slip dans list_and_sort_images
            with patch("app.main.list_and_sort_images",
                       side_effect=ZipSlipError("danger.jpg hors pages/")):
                with pytest.raises(ZipSlipError):
                    prep_main.run_job(meta_path)

        # Vérifier que le state.json indique ERROR
        import json as _j
        state = _j.loads(open(meta_path).read())
        assert state["state"] == "ERROR"
        assert "zip-slip" in state["message"].lower()

    def test_zip_slip_ne_produit_pas_raw_pdf(self, tmp_path):
        """run_job avec zip-slip → aucun raw.pdf créé."""
        import app.main as prep_main

        meta_path = self._make_job_file(tmp_path)
        job_dir = tmp_path / "work" / "test_job"
        raw_pdf = job_dir / "raw.pdf"

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "ok"
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc):
            with patch("app.main.list_and_sort_images",
                       side_effect=ZipSlipError("attaque détectée")):
                with pytest.raises(ZipSlipError):
                    prep_main.run_job(meta_path)

        assert not raw_pdf.exists(), "raw.pdf ne doit pas exister après un zip-slip"

