"""
Tests E2E minimal — tools/cli.py

Pipeline complet CBZ → PDF avec subprocess mocké (déterministe, sans outils système).
Un test "réel" optionnel est skippe automatiquement si 7z est absent.
"""
import os
import shutil
import sys
import zipfile

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Chemin vers make_test_cbz existant dans tests/e2e/
_E2E_DIR = os.path.join(_REPO_ROOT, "tests", "e2e")
if _E2E_DIR not in sys.path:
    sys.path.insert(0, _E2E_DIR)

from make_test_cbz import make_test_cbz
from tools.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cbz_file(tmp_path):
    """Crée un CBZ minimal (2 pages PNG) dans tmp_path."""
    out = str(tmp_path / "test_comic.cbz")
    return make_test_cbz(out, num_pages=2)


# ---------------------------------------------------------------------------
# E2E mocké (CI-safe : pas d'outils système requis)
# ---------------------------------------------------------------------------

class TestCliE2EMocked:
    """Pipeline E2E complet avec 7z et ocrmypdf entièrement mockés."""

    def test_pipeline_no_ocr_produit_pdf(self, tmp_path, cbz_file, mocker):
        """main() avec --no-ocr produit un PDF nommé correctement."""
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)

        # Mock : check_all_deps OK
        mocker.patch("tools.cli.check_all_deps", return_value={"7z": "/usr/bin/7z"})
        # Mock : require_tool retourne un chemin fictif
        mocker.patch("tools.cli.require_tool", return_value="/usr/bin/7z")
        # Mock : 7z réussit
        mocker.patch(
            "tools.cli.subprocess.run",
            return_value=mocker.Mock(returncode=0, stdout="Everything is Ok", stderr=""),
        )
        # Mock : list_and_sort_images retourne 2 images fictives
        fake_images = [str(tmp_path / "001.png"), str(tmp_path / "002.png")]
        for img in fake_images:
            with open(img, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        mocker.patch("tools.cli.list_and_sort_images", return_value=fake_images)
        # Mock : images_to_pdf écrit un PDF valide
        def fake_images_to_pdf(images, dest):
            with open(dest, "wb") as f:
                f.write(b"%PDF-1.4" + b"\x00" * 2048)
        mocker.patch("tools.cli.images_to_pdf", side_effect=fake_images_to_pdf)

        result = main([cbz_file, "--out", out_dir, "--no-ocr"])

        assert result == 0
        # Vérifier qu'un PDF a été produit dans out_dir
        pdfs = [f for f in os.listdir(out_dir) if f.endswith(".pdf")]
        assert len(pdfs) == 1
        assert "test_comic" in pdfs[0]
        assert "__job-" in pdfs[0]
        # Vérifier le contenu minimal du PDF
        with open(os.path.join(out_dir, pdfs[0]), "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_pipeline_avec_ocr_produit_pdf(self, tmp_path, cbz_file, mocker):
        """main() avec OCR produit un PDF nommé correctement."""
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)

        mocker.patch("tools.cli.check_all_deps",
                     return_value={"7z": "/usr/bin/7z", "ocrmypdf": "/usr/bin/ocrmypdf"})
        mocker.patch("tools.cli.require_tool", side_effect=lambda t: f"/usr/bin/{t}")
        # 7z + ocrmypdf mock : deux appels subprocess.run
        call_count = {"n": 0}

        def fake_run(cmd, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # 7z extraction
                return mocker.Mock(returncode=0, stdout="OK", stderr="")
            else:
                # ocrmypdf : écrire un PDF valide dans la destination (avant-dernier arg)
                dest = cmd[-1]
                with open(dest, "wb") as f:
                    f.write(b"%PDF-1.4" + b"\x00" * 2048)
                return mocker.Mock(returncode=0, stdout="", stderr="")

        mocker.patch("tools.cli.subprocess.run", side_effect=fake_run)
        fake_images = [str(tmp_path / "001.png")]
        with open(fake_images[0], "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        mocker.patch("tools.cli.list_and_sort_images", return_value=fake_images)

        def fake_images_to_pdf(images, dest):
            with open(dest, "wb") as f:
                f.write(b"%PDF-1.4" + b"\x00" * 2048)
        mocker.patch("tools.cli.images_to_pdf", side_effect=fake_images_to_pdf)

        result = main([cbz_file, "--out", out_dir, "--lang", "fra"])
        assert result == 0
        pdfs = [f for f in os.listdir(out_dir) if f.endswith(".pdf")]
        assert len(pdfs) == 1

    def test_fichier_deja_produit_ne_relance_pas(self, tmp_path, cbz_file, mocker):
        """Si le PDF de sortie existe déjà, le pipeline est ignoré (idempotent)."""
        from tools.pipeline_core import sha256_file, make_job_key, output_filename
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)

        file_hash = sha256_file(cbz_file)
        _, job_key = make_job_key(file_hash, "fra+eng")
        out_name = output_filename(cbz_file, job_key)
        existing_pdf = os.path.join(out_dir, out_name)
        with open(existing_pdf, "wb") as f:
            f.write(b"%PDF-1.4" + b"\x00" * 2048)

        mocker.patch("tools.cli.check_all_deps", return_value={"7z": "/usr/bin/7z"})
        mock_run = mocker.patch("tools.cli.subprocess.run")

        result = main([cbz_file, "--out", out_dir, "--no-ocr"])
        assert result == 0
        # subprocess.run ne doit pas avoir été appelé (PDF déjà présent)
        mock_run.assert_not_called()

    def test_nommage_output_conforme(self, tmp_path, cbz_file, mocker):
        """Le nom du PDF suit la convention <nom>__job-<jobKey>.pdf."""
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)

        mocker.patch("tools.cli.check_all_deps", return_value={"7z": "/usr/bin/7z"})
        mocker.patch("tools.cli.require_tool", return_value="/usr/bin/7z")
        mocker.patch(
            "tools.cli.subprocess.run",
            return_value=mocker.Mock(returncode=0, stdout="OK", stderr=""),
        )
        fake_img = str(tmp_path / "001.png")
        with open(fake_img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        mocker.patch("tools.cli.list_and_sort_images", return_value=[fake_img])

        def fake_images_to_pdf(images, dest):
            with open(dest, "wb") as f:
                f.write(b"%PDF-1.4" + b"\x00" * 2048)
        mocker.patch("tools.cli.images_to_pdf", side_effect=fake_images_to_pdf)

        main([cbz_file, "--out", out_dir, "--no-ocr"])

        pdfs = [f for f in os.listdir(out_dir) if f.endswith(".pdf")]
        assert len(pdfs) == 1
        name = pdfs[0]
        assert name.startswith("test_comic__job-")
        assert name.endswith(".pdf")
        # Le jobKey doit avoir le format fileHash__profileHash
        job_part = name[len("test_comic__job-"):-len(".pdf")]
        assert "__" in job_part


# ---------------------------------------------------------------------------
# E2E "réel" optionnel (skipif 7z absent)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("7z") is None and shutil.which("7za") is None,
    reason="7z non disponible dans le PATH — test réel ignoré en CI",
)
class TestCliE2EReal:
    """Pipeline E2E réel avec 7z système (skipé si 7z absent)."""

    def test_pipeline_real_no_ocr(self, tmp_path, cbz_file):
        """Pipeline réel avec --no-ocr : extraction 7z + img2pdf."""
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)

        result = main([cbz_file, "--out", out_dir, "--no-ocr"])
        assert result == 0

        pdfs = [f for f in os.listdir(out_dir) if f.endswith(".pdf")]
        assert len(pdfs) == 1
        pdf_path = os.path.join(out_dir, pdfs[0])
        assert os.path.getsize(pdf_path) > 1024
        with open(pdf_path, "rb") as f:
            assert f.read(5) == b"%PDF-"

