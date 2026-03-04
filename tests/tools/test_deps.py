"""
Tests unitaires — tools/deps.py

Vérifie la détection des dépendances (find_tool, require_tool, check_all_deps)
sans aucun outil système réel requis (shutil.which entièrement mocké).
"""
import os
import sys

import pytest

# Ajouter la racine du repo au path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.deps import (
    MissingDepError,
    find_tool,
    require_tool,
    check_all_deps,
    check_deps_report,
)


# ---------------------------------------------------------------------------
# find_tool
# ---------------------------------------------------------------------------

class TestFindTool:
    """Tests de la fonction find_tool."""

    def test_trouve_outil_present(self, mocker):
        """find_tool retourne le chemin si l'outil est dans le PATH."""
        mocker.patch("shutil.which", return_value="/usr/bin/7z")
        result = find_tool("7z")
        assert result == "/usr/bin/7z"

    def test_retourne_none_si_absent(self, mocker):
        """find_tool retourne None si aucun candidat n'est dans le PATH."""
        mocker.patch("shutil.which", return_value=None)
        result = find_tool("7z")
        assert result is None

    def test_essaie_alias_7z(self, mocker):
        """find_tool essaie les alias de 7z (7z, 7za, 7zz)."""
        calls = []

        def fake_which(name):
            calls.append(name)
            return "/usr/bin/7za" if name == "7za" else None

        mocker.patch("shutil.which", side_effect=fake_which)
        result = find_tool("7z")
        assert result == "/usr/bin/7za"
        assert "7z" in calls
        assert "7za" in calls

    def test_essaie_alias_ghostscript(self, mocker):
        """find_tool essaie les alias de ghostscript (gs, gswin64c, gswin32c)."""
        def fake_which(name):
            return "/usr/bin/gs" if name == "gs" else None

        mocker.patch("shutil.which", side_effect=fake_which)
        result = find_tool("ghostscript")
        assert result == "/usr/bin/gs"

    def test_essaie_variante_exe_sur_windows(self, mocker):
        """find_tool essaie la variante .exe pour les outils non-alias."""
        def fake_which(name):
            return "C:\\bin\\ocrmypdf.exe" if name == "ocrmypdf.exe" else None

        mocker.patch("shutil.which", side_effect=fake_which)
        result = find_tool("ocrmypdf")
        assert result == "C:\\bin\\ocrmypdf.exe"


# ---------------------------------------------------------------------------
# require_tool
# ---------------------------------------------------------------------------

class TestRequireTool:
    """Tests de la fonction require_tool."""

    def test_retourne_chemin_si_present(self, mocker):
        """require_tool retourne le chemin si l'outil est disponible."""
        mocker.patch("tools.deps.find_tool", return_value="/usr/bin/7z")
        result = require_tool("7z")
        assert result == "/usr/bin/7z"

    def test_leve_missing_dep_error_si_absent(self, mocker):
        """require_tool lève MissingDepError si l'outil est absent."""
        mocker.patch("tools.deps.find_tool", return_value=None)
        with pytest.raises(MissingDepError) as exc_info:
            require_tool("7z")
        assert exc_info.value.tool == "7z"

    def test_message_erreur_actionnable_7z(self, mocker):
        """Le message d'erreur de MissingDepError pour 7z contient un hint d'installation."""
        mocker.patch("tools.deps.find_tool", return_value=None)
        with pytest.raises(MissingDepError) as exc_info:
            require_tool("7z")
        message = str(exc_info.value)
        assert "7-Zip" in message or "7z" in message.lower()
        # Doit contenir au moins un lien ou commande d'installation
        assert "apt" in message or "brew" in message or "https://" in message

    def test_message_erreur_actionnable_ocrmypdf(self, mocker):
        """Le message d'erreur pour ocrmypdf mentionne pip install."""
        mocker.patch("tools.deps.find_tool", return_value=None)
        with pytest.raises(MissingDepError) as exc_info:
            require_tool("ocrmypdf")
        assert "pip install ocrmypdf" in str(exc_info.value)

    def test_message_erreur_outil_inconnu(self, mocker):
        """require_tool produit un message générique pour un outil inconnu."""
        mocker.patch("tools.deps.find_tool", return_value=None)
        with pytest.raises(MissingDepError) as exc_info:
            require_tool("unknown_tool_xyz")
        assert "unknown_tool_xyz" in str(exc_info.value)


# ---------------------------------------------------------------------------
# check_all_deps
# ---------------------------------------------------------------------------

class TestCheckAllDeps:
    """Tests de la fonction check_all_deps."""

    def test_retourne_dict_si_tous_presents(self, mocker):
        """check_all_deps retourne un dict complet si tous les outils sont présents."""
        mocker.patch("tools.deps.require_tool", side_effect=lambda t: f"/usr/bin/{t}")
        result = check_all_deps()
        assert "7z" in result
        assert "ocrmypdf" in result
        assert "tesseract" in result
        assert "ghostscript" in result

    def test_exclut_ocr_si_no_ocr(self, mocker):
        """check_all_deps(no_ocr=True) ne vérifie pas ocrmypdf/tesseract/ghostscript."""
        mocker.patch("tools.deps.require_tool", side_effect=lambda t: f"/usr/bin/{t}")
        result = check_all_deps(no_ocr=True)
        assert "7z" in result
        assert "ocrmypdf" not in result
        assert "tesseract" not in result

    def test_leve_exception_si_7z_absent(self, mocker):
        """check_all_deps lève MissingDepError si 7z est absent."""
        def fake_require(tool):
            if tool == "7z":
                raise MissingDepError("7z", "7-Zip manquant")
            return f"/usr/bin/{tool}"

        mocker.patch("tools.deps.require_tool", side_effect=fake_require)
        with pytest.raises(MissingDepError) as exc_info:
            check_all_deps()
        assert exc_info.value.tool == "7z"


# ---------------------------------------------------------------------------
# check_deps_report
# ---------------------------------------------------------------------------

class TestCheckDepsReport:
    """Tests de la fonction check_deps_report."""

    def test_rapport_ok_si_tous_presents(self, mocker):
        """check_deps_report retourne 'OK' si tous les outils sont présents."""
        mocker.patch("tools.deps.find_tool", return_value="/usr/bin/tool")
        mocker.patch("tools.deps._get_version", return_value="1.0")
        mocker.patch.dict("sys.modules", {"img2pdf": type(sys)("img2pdf")})
        # Simuler img2pdf installé
        import types
        fake_img2pdf = types.ModuleType("img2pdf")
        fake_img2pdf.__version__ = "0.5.1"
        mocker.patch.dict("sys.modules", {"img2pdf": fake_img2pdf})
        report = check_deps_report()
        assert "OK" in report

    def test_rapport_erreur_si_outil_absent(self, mocker):
        """check_deps_report contient 'ABSENT' si un outil manque."""
        mocker.patch("tools.deps.find_tool", return_value=None)
        report = check_deps_report()
        assert "ABSENT" in report
        assert "ERREUR" in report

    def test_rapport_contient_noms_outils(self, mocker):
        """check_deps_report liste les noms de tous les outils vérifiés."""
        mocker.patch("tools.deps.find_tool", return_value=None)
        report = check_deps_report()
        assert "7z" in report
        assert "ocrmypdf" in report
        assert "tesseract" in report
        assert "ghostscript" in report

