import os, json, time, hashlib, re, shutil
from typing import Any, Dict, Optional, List, Set

# ---------------------------------------------------------------------------
# Fonctions existantes (inchangées)
# ---------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

_num_re = re.compile(r"(\d+)")

def natural_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in _num_re.split(s)]

def list_images_recursive(root: str) -> List[str]:
    exts = {".jpg",".jpeg",".png",".webp",".tif",".tiff",".bmp"}
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in exts:
                out.append(os.path.join(dirpath, fn))
    out.sort(key=lambda p: natural_key(os.path.basename(p)))
    return out

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# B2 — Validation PDF
# ---------------------------------------------------------------------------

def validate_pdf(path: str, min_size_bytes: int = 1024) -> bool:
    """
    Vérifie qu'un fichier est un PDF valide (header %PDF + taille minimale).

    :param path: Chemin du fichier à vérifier.
    :param min_size_bytes: Taille minimale acceptée en octets.
    :return: True si le fichier semble valide, False sinon.
    """
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < min_size_bytes:
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(5)
        return header == b"%PDF-"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# B4 — Vérification espace disque
# ---------------------------------------------------------------------------

def check_disk_space(work_dir: str, input_size_bytes: int, factor: float = 2.0) -> bool:
    """
    Vérifie qu'il y a suffisamment d'espace disque libre pour traiter un fichier.

    :param work_dir: Répertoire de travail (utilisé pour la mesure d'espace libre).
    :param input_size_bytes: Taille du fichier d'entrée en octets.
    :param factor: Facteur multiplicatif de sécurité (espace requis = input_size * factor).
    :return: True si l'espace est suffisant, False sinon.
    """
    try:
        ensure_dir(work_dir)
        free = shutil.disk_usage(work_dir).free
        needed = int(input_size_bytes * factor)
        return free >= needed
    except Exception:
        return True  # En cas d'erreur de mesure, on laisse passer


# ---------------------------------------------------------------------------
# B5 — Nettoyage des workdirs anciens
# ---------------------------------------------------------------------------

def cleanup_old_workdirs(work_dir: str, keep_days: int, running_job_keys: Set[str]) -> int:
    """
    Supprime les sous-dossiers de ``work_dir`` plus anciens que ``keep_days`` jours,
    en ignorant ceux dont la clé est dans ``running_job_keys``.

    :param work_dir: Répertoire contenant les dossiers de travail.
    :param keep_days: Nombre de jours à conserver (0 = supprimer immédiatement tout DONE).
    :param running_job_keys: Ensemble des jobKeys en cours d'exécution (ne jamais supprimer).
    :return: Nombre de dossiers supprimés.
    """
    if not os.path.isdir(work_dir):
        return 0
    cutoff = time.time() - keep_days * 86400
    deleted = 0
    for name in os.listdir(work_dir):
        if name.startswith("_"):
            continue  # Ignorer _staging et autres dossiers système
        if name in running_job_keys:
            continue
        full = os.path.join(work_dir, name)
        if not os.path.isdir(full):
            continue
        try:
            mtime = os.path.getmtime(full)
            if mtime < cutoff:
                shutil.rmtree(full, ignore_errors=True)
                deleted += 1
        except Exception:
            pass
    return deleted


# ---------------------------------------------------------------------------
# E1 — Vérification taille fichier entrant
# ---------------------------------------------------------------------------

def check_input_size(path: str, max_mb: float = 500.0) -> bool:
    """
    Vérifie que la taille du fichier d'entrée ne dépasse pas le maximum autorisé.

    :param path: Chemin du fichier.
    :param max_mb: Taille maximale en mégaoctets.
    :return: True si la taille est acceptable, False si le fichier est trop grand.
    """
    try:
        size = os.path.getsize(path)
        return size <= max_mb * 1024 * 1024
    except Exception:
        return False


# ---------------------------------------------------------------------------
# E2 — Vérification signature ZIP/RAR
# ---------------------------------------------------------------------------

# Signatures magiques connues pour CBZ (ZIP) et CBR (RAR4 + RAR5)
_MAGIC_ZIP  = b"\x50\x4B\x03\x04"           # ZIP : 50 4B 03 04
_MAGIC_RAR4 = b"\x52\x61\x72\x21\x1A\x07\x00"      # RAR4 : 52 61 72 21 1A 07 00
_MAGIC_RAR5 = b"\x52\x61\x72\x21\x1A\x07\x01\x00"  # RAR5 : 52 61 72 21 1A 07 01 00


def check_file_signature(path: str) -> bool:
    """
    Vérifie que le fichier possède une signature magique ZIP ou RAR valide.
    CBZ = archive ZIP, CBR = archive RAR4 ou RAR5.

    :param path: Chemin du fichier à vérifier.
    :return: True si la signature est reconnue (ZIP ou RAR), False sinon.
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
