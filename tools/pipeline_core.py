"""
Module pipeline_core — fonctions pures autonomes du pipeline comic2pdf.

Copie/adaptation des fonctions clés des services (prep, ocr, orchestrator)
pour usage dans les outils CLI/watch sans imports croisés vers services/*/app/.
Aucun import depuis services/ : ce module est totalement autonome.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import img2pdf as _img2pdf
    _HAS_IMG2PDF = True
except ImportError:  # pragma: no cover
    _img2pdf = None
    _HAS_IMG2PDF = False

# ---------------------------------------------------------------------------
# Constantes images
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
_PARASITES = {"thumbs.db", ".ds_store", "desktop.ini"}
_PARASITE_DIRS = {"__macosx"}

# Signatures magiques ZIP/RAR
_MAGIC_ZIP  = b"\x50\x4B\x03\x04"
_MAGIC_RAR4 = b"\x52\x61\x72\x21\x1A\x07\x00"
_MAGIC_RAR5 = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

# ---------------------------------------------------------------------------
# Utilitaires FS
# ---------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """Crée le répertoire (et ses parents) s'il n'existe pas.

    :param path: Chemin du répertoire à créer.
    """
    os.makedirs(path, exist_ok=True)


def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    """Écrit ``data`` dans ``path`` de manière atomique (.tmp + rename).

    :param path: Chemin de destination du fichier JSON.
    :param data: Données à sérialiser.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def read_json(path: str) -> Optional[Dict[str, Any]]:
    """Lit un fichier JSON et retourne son contenu, ou None s'il n'existe pas.

    :param path: Chemin du fichier JSON.
    :return: Contenu désérialisé, ou None.
    """
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Calcule le SHA-256 hexadécimal d'un fichier.

    :param path: Chemin du fichier.
    :param chunk_size: Taille des blocs de lecture en octets.
    :return: Hash hex (64 caractères).
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


_num_re = re.compile(r"(\d+)")


def natural_key(s: str) -> list:
    """Clé de tri naturel : segments numériques comparés en tant qu'entiers.

    :param s: Chaîne à décomposer.
    :return: Liste mixte str/int pour comparaison.
    """
    return [int(t) if t.isdigit() else t.lower() for t in _num_re.split(s)]


def now_iso() -> str:
    """Retourne la date/heure courante au format ISO 8601 UTC.

    :return: Chaîne ISO 8601, ex: ``"2026-03-04T12:00:00Z"``.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def validate_pdf(path: str, min_size_bytes: int = 1024) -> bool:
    """Vérifie qu'un fichier est un PDF valide (header %PDF- + taille minimale).

    :param path: Chemin du fichier.
    :param min_size_bytes: Taille minimale acceptée en octets.
    :return: True si valide, False sinon.
    """
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < min_size_bytes:
        return False
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False


def check_file_signature(path: str) -> bool:
    """Vérifie la signature magique ZIP ou RAR du fichier.

    :param path: Chemin du fichier.
    :return: True si la signature est reconnue, False sinon.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return (
            header[:4] == _MAGIC_ZIP
            or header[:7] == _MAGIC_RAR4
            or header[:8] == _MAGIC_RAR5
        )
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Protection zip-slip
# ---------------------------------------------------------------------------

class ZipSlipError(Exception):
    """Levée lorsqu'un fichier extrait sort du répertoire pages/ attendu."""


def check_zip_slip(pages_dir: str, images: List[str]) -> List[str]:
    """Vérifie que tous les chemins restent sous ``pages_dir`` (protection zip-slip).

    :param pages_dir: Répertoire d'extraction attendu.
    :param images: Liste de chemins d'images.
    :return: La liste si tous les chemins sont sûrs.
    :raises ZipSlipError: Si un chemin sort de ``pages_dir``.
    """
    real_base = os.path.realpath(os.path.abspath(pages_dir))
    unsafe = []
    for path in images:
        real_path = os.path.realpath(os.path.abspath(path))
        if not (real_path.startswith(real_base + os.sep) or real_path == real_base):
            unsafe.append(path)
    if unsafe:
        raise ZipSlipError(
            f"Zip-slip détecté : {len(unsafe)} fichier(s) hors de '{pages_dir}' — "
            f"exemple : '{unsafe[0]}'"
        )
    return images

# ---------------------------------------------------------------------------
# Filtrage et tri des images
# ---------------------------------------------------------------------------

def filter_images(root: str) -> List[str]:
    """Retourne la liste des fichiers images valides sous ``root``, récursivement.

    :param root: Dossier racine à parcourir.
    :return: Liste de chemins absolus vers les images.
    """
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in _PARASITE_DIRS]
        for fn in filenames:
            if fn.lower() in _PARASITES:
                continue
            if os.path.splitext(fn)[1].lower() in IMAGE_EXTENSIONS:
                out.append(os.path.join(dirpath, fn))
    return out


def sort_images(paths: List[str]) -> List[str]:
    """Trie une liste de chemins d'images par tri naturel.

    :param paths: Liste de chemins.
    :return: Liste triée.
    """
    return sorted(paths, key=lambda p: natural_key(os.path.basename(p)))


def list_and_sort_images(root: str) -> List[str]:
    """Filtre, trie et vérifie la protection zip-slip sous ``root``.

    :param root: Dossier racine (pages_dir après extraction).
    :return: Liste triée de chemins d'images sûrs.
    :raises ZipSlipError: Si un chemin sort de ``root``.
    """
    return check_zip_slip(root, sort_images(filter_images(root)))

# ---------------------------------------------------------------------------
# Génération PDF
# ---------------------------------------------------------------------------

def images_to_pdf(images: List[str], dest_path: str) -> None:
    """Convertit une liste d'images en PDF via img2pdf (écriture atomique).

    :param images: Liste ordonnée de chemins d'images.
    :param dest_path: Chemin de destination du PDF.
    :raises ImportError: Si img2pdf n'est pas installé.
    :raises ValueError: Si la liste d'images est vide.
    :raises RuntimeError: Si img2pdf échoue.
    """
    if not _HAS_IMG2PDF:
        raise ImportError("img2pdf n'est pas installé (pip install img2pdf)")
    if not images:
        raise ValueError("La liste d'images est vide, impossible de générer un PDF.")
    tmp_path = dest_path + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(_img2pdf.convert(images))
        os.replace(tmp_path, dest_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        raise

# ---------------------------------------------------------------------------
# Commande OCR
# ---------------------------------------------------------------------------

def build_ocrmypdf_cmd(
    raw_pdf: str,
    dest: str,
    *,
    lang: str = "fra+eng",
    rotate: bool = True,
    deskew: bool = True,
    optimize: int = 1,
) -> List[str]:
    """Construit la commande ocrmypdf.

    :param raw_pdf: Chemin du PDF source.
    :param dest: Chemin du PDF de sortie.
    :param lang: Langue(s) Tesseract (ex: ``"fra+eng"``).
    :param rotate: Activer la correction de rotation.
    :param deskew: Activer la correction d'inclinaison.
    :param optimize: Niveau d'optimisation (0–3).
    :return: Liste de tokens formant la commande.
    """
    cmd = ["ocrmypdf", "--output-type", "pdf"]
    if rotate:
        cmd.append("--rotate-pages")
    if deskew:
        cmd.append("--deskew")
    cmd += ["--optimize", str(optimize)]
    if lang:
        cmd += ["-l", lang]
    cmd += [raw_pdf, dest]
    return cmd

# ---------------------------------------------------------------------------
# JobKey (déduplication)
# ---------------------------------------------------------------------------

def stable_json(obj: dict) -> str:
    """Sérialise un dict en JSON compact déterministe (clés triées).

    :param obj: Objet à sérialiser.
    :return: Chaîne JSON canonique.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_str(s: str) -> str:
    """Calcule le SHA-256 hexadécimal d'une chaîne UTF-8.

    :param s: Chaîne d'entrée.
    :return: Hash hex (64 caractères).
    """
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_job_key(file_hash: str, lang: str = "fra+eng") -> Tuple[str, str]:
    """Calcule le jobKey = ``fileHash__profileHash`` pour le mode local.

    Le profil local est minimal : uniquement la langue normalisée.

    :param file_hash: SHA-256 hexadécimal du fichier source.
    :param lang: Langue(s) OCR (normalisée : tokens triés).
    :return: Tuple ``(profile_hash, job_key)``.
    """
    normalized_lang = "+".join(sorted(set(lang.split("+"))))
    profile = {"lang": normalized_lang}
    profile_hash = sha256_str(stable_json(profile))
    job_key = f"{file_hash}__{profile_hash}"
    return profile_hash, job_key


def output_filename(input_path: str, job_key: str) -> str:
    """Retourne le nom du PDF de sortie selon la convention ``<nom>__job-<jobKey>.pdf``.

    :param input_path: Chemin du fichier source.
    :param job_key: Clé du job.
    :return: Nom de fichier (sans répertoire).
    """
    base = os.path.splitext(os.path.basename(input_path))[0]
    return f"{base}__job-{job_key}.pdf"

