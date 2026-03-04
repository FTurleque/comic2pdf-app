"""
Tests unitaires — tools/cli.py

Vérifie le parsing des arguments, la validation de l'input et le pipeline
(subprocess 7z + ocrmypdf entièrement mockés).
"""
import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.cli import build_parser, validate_input, main
from tools.deps import MissingDepError


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    """Tests du parser argparse CLI."""

    def test_input_obligatoire(self):
        """Sans --check-deps et sans input, main retourne EXIT_ERR."""
        result = main([])
        assert result != 0

    def test_check_deps_sans_input(self, mocker, capsys):
        """--check-deps seul ne requiert pas de fichier input."""
        mocker.patch("tools.cli.check_deps_report", return_value="OK — tout est présent.")
        result = main(["--check-deps"])
        assert result == 0
        out = capsys.readouterr().out
        assert "OK" in out

    def test_lang_par_defaut(self):
        """La langue par défaut est fra+eng."""
        parser = build_parser()
        args = parser.parse_args(["mon.cbz"])
        assert args.lang == "fra+eng"

    def test_out_par_defaut(self):
        """Le dossier de sortie par défaut est '.'."""
        parser = build_parser()
        args = parser.parse_args(["mon.cbz"])
        assert args.out == "."

    def test_no_ocr_flag(self):
        """--no-ocr positionne le flag à True."""
        parser = build_parser()
        args = parser.parse_args(["mon.cbz", "--no-ocr"])
        assert args.no_ocr is True

    def test_keep_temp_flag(self):
        """--keep-temp positionne le flag à True."""
        parser = build_parser()
        args = parser.parse_args(["mon.cbz", "--keep-temp"])
        assert args.keep_temp is True

    def test_lang_personnalise(self):
        """--lang accepte une valeur personnalisée."""
        parser = build_parser()
        args = parser.parse_args(["mon.cbz", "--lang", "deu"])
        assert args.lang == "deu"


# ---------------------------------------------------------------------------
# validate_input
# ---------------------------------------------------------------------------

class TestValidateInput:
    """Tests de la validation du fichier d'entrée."""

    def test_fichier_inexistant_leve_systemexit(self, tmp_path):
        """validate_input lève SystemExit si le fichier n'existe pas."""
        with pytest.raises(SystemExit):
            validate_input(str(tmp_path / "absent.cbz"))

    def test_extension_invalide_leve_systemexit(self, tmp_path):
        """validate_input lève SystemExit pour une extension non supportée."""
        p = str(tmp_path / "fichier.pdf")
        with open(p, "wb") as f:
            f.write(b"\x50\x4B\x03\x04" + b"\x00" * 8)
        with pytest.raises(SystemExit):
            validate_input(p)

    def test_signature_invalide_leve_systemexit(self, tmp_path):
        """validate_input lève SystemExit pour une signature invalide."""
        p = str(tmp_path / "mauvais.cbz")
        with open(p, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07")
        with pytest.raises(SystemExit):
            validate_input(p)

    def test_fichier_valide_ne_leve_pas(self, tmp_path):
        """validate_input ne lève pas pour un CBZ valide."""
        p = str(tmp_path / "ok.cbz")
        with open(p, "wb") as f:
            f.write(b"\x50\x4B\x03\x04" + b"\x00" * 8)
        # Ne doit pas lever
        validate_input(p)


# ---------------------------------------------------------------------------
# main() — pipeline mocké
# ---------------------------------------------------------------------------

class TestMain:
    """Tests du pipeline via main() avec subprocess entièrement mocké."""

    def _make_valid_cbz(self, tmp_path: object) -> str:
        """Crée un CBZ valide (signature ZIP) dans tmp_path."""
        import zipfile
        p = str(tmp_path / "test.cbz")
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("001.jpg", b"\xff\xd8\xff" + b"\x00" * 100)
        return p

    def test_deps_manquantes_retourne_1(self, tmp_path, mocker):
        """main() retourne 1 si une dépendance est manquante."""
        cbz = self._make_valid_cbz(tmp_path)
        mocker.patch(
            "tools.cli.check_all_deps",
            side_effect=MissingDepError("7z", "7z manquant"),
        )
        result = main([cbz])
        assert result == 1

    def test_pipeline_succes(self, tmp_path, mocker):
        """main() retourne 0 si le pipeline réussit (tout mocké)."""
        cbz = self._make_valid_cbz(tmp_path)
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir, exist_ok=True)

        # Mock : dépendances OK
        mocker.patch("tools.cli.check_all_deps", return_value={"7z": "/usr/bin/7z"})
        # Mock : require_tool retourne un chemin fictif (appelé dans _step_extract)
        mocker.patch("tools.cli.require_tool", return_value="/usr/bin/7z")
        # Mock : extraction 7z
        mocker.patch(
            "tools.cli.subprocess.run",
            return_value=mocker.Mock(returncode=0, stdout="OK", stderr=""),
        )
        # Mock : images_to_pdf
        def fake_images_to_pdf(images, dest):
            with open(dest, "wb") as f:
                f.write(b"%PDF-1.4" + b"\x00" * 2000)

        mocker.patch("tools.cli.images_to_pdf", side_effect=fake_images_to_pdf)
        # Mock : list_and_sort_images retourne 1 image
        fake_img = str(tmp_path / "001.jpg")
        with open(fake_img, "wb") as f:
            f.write(b"\x00" * 10)
        mocker.patch("tools.cli.list_and_sort_images", return_value=[fake_img])
        # --no-ocr pour éviter d'appeler ocrmypdf
        result = main([cbz, "--out", out_dir, "--no-ocr"])
        assert result == 0

    def test_pipeline_7z_echec_retourne_1(self, tmp_path, mocker):
        """main() retourne 1 si 7z échoue."""
        cbz = self._make_valid_cbz(tmp_path)
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir, exist_ok=True)

        mocker.patch("tools.cli.check_all_deps", return_value={"7z": "/usr/bin/7z"})
        mocker.patch(
            "tools.cli.subprocess.run",
            return_value=mocker.Mock(returncode=1, stdout="", stderr="7z error"),
        )
        result = main([cbz, "--out", out_dir, "--no-ocr"])
        assert result == 1

    def test_check_deps_seul(self, mocker, capsys):
        """--check-deps affiche le rapport et retourne 0."""
        mocker.patch("tools.cli.check_deps_report", return_value="OK")
        result = main(["--check-deps"])
        assert result == 0
        assert "OK" in capsys.readouterr().out


