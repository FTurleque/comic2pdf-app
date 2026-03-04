"""
Module deps — détection des dépendances externes requises par le pipeline local.

Outils requis : 7z (extraction CBZ/CBR), ocrmypdf (OCR), tesseract, ghostscript.
Chaque fonction retourne le chemin résolu de l'outil, ou lève ``MissingDepError``
avec un message d'erreur actionnable indiquant comment installer l'outil manquant.
"""
import shutil
import subprocess
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class MissingDepError(Exception):
    """Levée lorsqu'une dépendance externe est introuvable dans le PATH.

    :param tool: Nom de l'outil manquant.
    :param message: Message d'installation actionnable.
    """
    def __init__(self, tool: str, message: str) -> None:
        self.tool = tool
        super().__init__(message)

# ---------------------------------------------------------------------------
# Messages d'installation par outil
# ---------------------------------------------------------------------------

_INSTALL_HINTS: Dict[str, str] = {
    "7z": (
        "7-Zip est introuvable dans le PATH.\n"
        "  Windows : https://www.7-zip.org/download.html  (installer puis ajouter au PATH)\n"
        "  Linux   : sudo apt install p7zip-full   # Debian/Ubuntu\n"
        "            sudo dnf install p7zip         # Fedora\n"
        "  macOS   : brew install p7zip"
    ),
    "ocrmypdf": (
        "ocrmypdf est introuvable dans le PATH.\n"
        "  Installer via pip : pip install ocrmypdf\n"
        "  Puis installer les binaires système :\n"
        "    Windows : https://github.com/ocrmypdf/OCRmyPDF/blob/main/docs/installation.md\n"
        "    Linux   : sudo apt install tesseract-ocr ghostscript\n"
        "    macOS   : brew install tesseract ghostscript"
    ),
    "tesseract": (
        "tesseract est introuvable dans le PATH.\n"
        "  Windows : https://github.com/UB-Mannheim/tesseract/wiki\n"
        "  Linux   : sudo apt install tesseract-ocr\n"
        "  macOS   : brew install tesseract"
    ),
    "ghostscript": (
        "ghostscript (gs) est introuvable dans le PATH.\n"
        "  Windows : https://www.ghostscript.com/download/gsdnld.html\n"
        "  Linux   : sudo apt install ghostscript\n"
        "  macOS   : brew install ghostscript"
    ),
}

# ---------------------------------------------------------------------------
# Détection d'un outil (Windows + Linux)
# ---------------------------------------------------------------------------

def find_tool(name: str) -> Optional[str]:
    """Recherche un outil dans le PATH (Windows + Linux/macOS).

    Essaie plusieurs variantes : ``name``, ``name.exe``, et les alias connus
    (ex: ``gs`` pour ghostscript).

    :param name: Nom de l'outil (ex: ``"7z"``, ``"ocrmypdf"``).
    :return: Chemin absolu résolu, ou None si introuvable.
    """
    candidates: List[str] = [name]

    # Alias connus
    _aliases = {
        "ghostscript": ["gs", "gswin64c", "gswin32c"],
        "7z": ["7z", "7za", "7zz"],
    }
    if name in _aliases:
        candidates = _aliases[name]
    else:
        # Toujours tenter la variante .exe sur Windows
        if not name.endswith(".exe"):
            candidates.append(name + ".exe")

    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def require_tool(name: str) -> str:
    """Retourne le chemin de l'outil ou lève ``MissingDepError``.

    :param name: Nom de l'outil (clé dans ``_INSTALL_HINTS``).
    :return: Chemin absolu de l'outil.
    :raises MissingDepError: Si l'outil est absent du PATH.
    """
    path = find_tool(name)
    if path is None:
        hint = _INSTALL_HINTS.get(name, f"'{name}' est introuvable dans le PATH.")
        raise MissingDepError(name, hint)
    return path

# ---------------------------------------------------------------------------
# Vérification de toutes les dépendances
# ---------------------------------------------------------------------------

def check_all_deps(*, no_ocr: bool = False) -> Dict[str, str]:
    """Vérifie la présence de toutes les dépendances du pipeline.

    :param no_ocr: Si True, les outils OCR (ocrmypdf, tesseract, ghostscript)
                   ne sont pas vérifiés.
    :return: Dict ``{outil: chemin_résolu}`` pour les outils trouvés.
    :raises MissingDepError: Dès le premier outil manquant.
    """
    tools_required = ["7z"]
    if not no_ocr:
        tools_required += ["ocrmypdf", "tesseract", "ghostscript"]

    result: Dict[str, str] = {}
    for tool in tools_required:
        result[tool] = require_tool(tool)
    return result


def check_deps_report(*, no_ocr: bool = False) -> str:
    """Retourne un rapport lisible de l'état de toutes les dépendances.

    Ne lève pas d'exception : les outils manquants sont signalés par ``ABSENT``.

    :param no_ocr: Si True, les outils OCR sont exclus du rapport.
    :return: Rapport multi-lignes lisible.
    """
    tools_to_check = ["7z"]
    if not no_ocr:
        tools_to_check += ["ocrmypdf", "tesseract", "ghostscript"]

    lines = ["Vérification des dépendances :"]
    all_ok = True
    for tool in tools_to_check:
        path = find_tool(tool)
        if path:
            version = _get_version(tool, path)
            lines.append(f"  ✓ {tool:<16} {path}  [{version}]")
        else:
            lines.append(f"  ✗ {tool:<16} ABSENT")
            all_ok = False

    # img2pdf (Python)
    try:
        import img2pdf
        lines.append(f"  ✓ img2pdf (py)   v{getattr(img2pdf, '__version__', '?')}")
    except ImportError:
        lines.append("  ✗ img2pdf (py)   ABSENT  →  pip install img2pdf")
        all_ok = False

    lines.append("")
    lines.append("OK — toutes les dépendances sont présentes." if all_ok
                 else "ERREUR — certaines dépendances sont manquantes.")
    return "\n".join(lines)


def _get_version(tool: str, path: str) -> str:
    """Tente de récupérer la version d'un outil via subprocess.

    :param tool: Nom logique de l'outil.
    :param path: Chemin résolu de l'outil.
    :return: Première ligne de la sortie version, ou ``"?"``.
    """
    _version_args: Dict[str, List[str]] = {
        "7z":          [path],
        "ocrmypdf":    [path, "--version"],
        "tesseract":   [path, "--version"],
        "ghostscript": [path, "--version"],
    }
    args = _version_args.get(tool, [path, "--version"])
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)
        out = (r.stdout or r.stderr).strip()
        return out.splitlines()[0] if out else "?"
    except Exception:
        return "?"

