"""
Module core de l'ocr-service.
Contient les fonctions pures testables sans démarrer de serveur FastAPI.
"""
import os
import subprocess
from typing import List

from app.utils import ensure_dir


def get_tool_versions() -> dict:
    """
    Récupère les versions des outils externes (ocrmypdf, tesseract, ghostscript).
    En cas d'erreur (outil absent), retourne ``"unknown"``.

    :return: Dict avec les clés ``ocrmypdf``, ``tesseract``, ``ghostscript``.
    """
    out: dict = {}
    try:
        p = subprocess.run(["ocrmypdf", "--version"], capture_output=True, text=True)
        out["ocrmypdf"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["ocrmypdf"] = "unknown"
    try:
        p = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        out["tesseract"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["tesseract"] = "unknown"
    try:
        p = subprocess.run(["gs", "--version"], capture_output=True, text=True)
        out["ghostscript"] = (p.stdout or p.stderr).strip().splitlines()[0]
    except Exception:
        out["ghostscript"] = "unknown"
    return out


def build_ocrmypdf_cmd(
    raw_pdf: str,
    dest: str,
    *,
    lang: str = "fra+eng",
    rotate: bool = True,
    deskew: bool = True,
    optimize: int = 1,
) -> List[str]:
    """
    Construit la liste d'arguments pour la commande ocrmypdf.

    :param raw_pdf: Chemin du PDF source (entrée).
    :param dest: Chemin du PDF de sortie (destination).
    :param lang: Langue(s) Tesseract, ex: ``"fra+eng"``.
    :param rotate: Activer la correction de rotation des pages.
    :param deskew: Activer la correction d'inclinaison.
    :param optimize: Niveau d'optimisation (0–3).
    :return: Liste de tokens formant la commande shell.
    """
    cmd = ["ocrmypdf", "--output-type", "pdf"]
    if rotate:
        cmd.append("--rotate-pages")
    if deskew:
        cmd.append("--deskew")
    if optimize is not None:
        cmd += ["--optimize", str(optimize)]
    if lang:
        cmd += ["-l", lang]
    cmd += [raw_pdf, dest]
    return cmd


def requeue_running(running_dir: str, queue_dir: str) -> int:
    """
    Déplace tous les jobs en état RUNNING depuis ``running_dir`` vers ``queue_dir``.
    Politique recalcul complet : aucun artefact existant n'est réutilisé.

    :param running_dir: Dossier des jobs en cours d'exécution.
    :param queue_dir: Dossier de la file d'attente.
    :return: Nombre de jobs remis en file.
    """
    ensure_dir(queue_dir)
    ensure_dir(running_dir)
    count = 0
    for fn in list(os.listdir(running_dir)):
        if not fn.endswith(".json"):
            continue
        src = os.path.join(running_dir, fn)
        dst = os.path.join(queue_dir, fn)
        try:
            os.replace(src, dst)
            count += 1
        except Exception:
            pass
    return count

