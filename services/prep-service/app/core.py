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
        dirnames[:] = [
            d for d in dirnames if d.lower() not in _PARASITE_DIRS
        ]
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

    :param root: Chemin du dossier racine.
    :return: Liste triée de chemins d'images valides.
    """
    return sort_images(filter_images(root))


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

