"""
Module core du prep-service.
Contient les fonctions pures testables sans démarrer de serveur FastAPI.
"""

import os
import subprocess
from typing import List

import img2pdf

# Extensions d'images supportées
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}

# Fichiers/dossiers parasites à ignorer
_PARASITES = {"thumbs.db", ".ds_store", "desktop.ini"}
_PARASITE_DIRS = {"__macosx"}


# ---------------------------------------------------------------------------
# Sécurité — protection zip-slip post-extraction
# ---------------------------------------------------------------------------


class ZipSlipError(Exception):
    """
    Levée lorsqu'un fichier extrait sort du répertoire ``pages/`` attendu.
    Indique une tentative d'attaque zip-slip (path traversal via archive malveillante).
    """


def check_zip_slip(pages_dir: str, images: List[str]) -> List[str]:
    """
    Vérifie que tous les chemins de ``images`` restent bien sous ``pages_dir``
    après résolution de chemin (protection zip-slip post-extraction).

    L'extraction est faite par 7z (subprocess) qui peut décompresser des archives
    malveillantes contenant des chemins traversants comme ``../../etc/crontab``.
    Cette vérification post-extraction est la ligne de défense principale.

    :param pages_dir: Répertoire d'extraction attendu (chemin canonique cible).
    :param images: Liste de chemins d'images retournés par ``filter_images()``.
    :return: Sous-liste des chemins strictement sous ``pages_dir``.
    :raises ZipSlipError: Si au moins un chemin sort de ``pages_dir``.
    """
    real_base = os.path.realpath(os.path.abspath(pages_dir))
    safe_images = []
    unsafe = []

    for path in images:
        real_path = os.path.realpath(os.path.abspath(path))
        if real_path.startswith(real_base + os.sep) or real_path == real_base:
            safe_images.append(path)
        else:
            unsafe.append(path)

    if unsafe:
        raise ZipSlipError(
            f"Zip-slip détecté : {len(unsafe)} fichier(s) hors de '{pages_dir}' — "
            f"exemple : '{unsafe[0]}'"
        )
    return safe_images


def filter_images(root: str) -> List[str]:
    """
    Retourne la liste des fichiers images valides sous ``root``, récursivement.
    Exclut les fichiers parasites (thumbs.db, .DS_Store, __MACOSX, etc.).

    :param root: Chemin du dossier racine à parcourir.
    :return: Liste de chemins absolus vers les images trouvées.
    """
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Ignorer les dossiers parasites (en place pour éviter de descendre dedans)
        dirnames[:] = [d for d in dirnames if d.lower() not in _PARASITE_DIRS]
        for fn in filenames:
            if fn.lower() in _PARASITES:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                out.append(os.path.join(dirpath, fn))
    return out


def sort_images(paths: List[str]) -> List[str]:
    """
    Trie une liste de chemins d'images par tri naturel (ordre numérique des noms de fichiers).
    Ex: [10.jpg, 2.jpg, 1.jpg] -> [1.jpg, 2.jpg, 10.jpg]

    :param paths: Liste de chemins à trier.
    :return: Nouvelle liste triée.
    """
    from app.utils import natural_key

    return sorted(paths, key=lambda p: natural_key(os.path.basename(p)))


def list_and_sort_images(root: str) -> List[str]:
    """
    Combine ``filter_images`` et ``sort_images`` : filtre puis trie.
    Inclut une vérification zip-slip : lève ``ZipSlipError`` si un fichier
    extrait sort du répertoire ``root`` (protection contre les archives malveillantes).

    :param root: Chemin du dossier racine (pages_dir après extraction 7z).
    :return: Liste triée de chemins d'images valides, tous sous ``root``.
    :raises ZipSlipError: Si un chemin sort de ``root`` après résolution.
    """
    images = sort_images(filter_images(root))
    return check_zip_slip(root, images)


def images_to_pdf(images: List[str], dest_path: str) -> None:
    """
    Convertit une liste d'images en un fichier PDF via img2pdf.
    Écrit d'abord dans un fichier temporaire ``dest_path + '.tmp'``,
    puis effectue un rename atomique vers ``dest_path``.

    :param images: Liste ordonnée de chemins d'images.
    :param dest_path: Chemin de destination du PDF généré.
    :raises ValueError: Si la liste d'images est vide.
    :raises RuntimeError: Si img2pdf échoue.
    """
    if not images:
        raise ValueError("La liste d'images est vide, impossible de générer un PDF.")
    tmp_path = dest_path + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(img2pdf.convert(images))
        os.replace(tmp_path, dest_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise


def get_tool_versions() -> dict:
    """
    Récupère les versions des outils externes (7z, img2pdf).
    En cas d'erreur, retourne ``"unknown"`` pour l'outil concerné.

    :return: Dict ``{"7z": str, "img2pdf": str}``.
    """
    out: dict = {}
    try:
        r = subprocess.run(["7z"], capture_output=True, text=True)
        first = (r.stdout.splitlines() or r.stderr.splitlines() or [""])[0]
        out["7z"] = first.strip()
    except Exception:
        out["7z"] = "unknown"
    out["img2pdf"] = getattr(img2pdf, "__version__", "unknown")
    return out
