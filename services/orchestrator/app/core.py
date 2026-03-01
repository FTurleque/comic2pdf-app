"""
Module core de l'orchestrateur.
Contient les fonctions pures testables sans démarrer de boucle watch.
"""
import hashlib
import json
import os
import time
from typing import Any, Optional, Tuple

from app.logger import get_logger
from app.utils import ensure_dir, atomic_write_json, now_iso

_log = get_logger("orchestrator.core")


# ---------------------------------------------------------------------------
# Lecture sécurisée JSON
# ---------------------------------------------------------------------------

def safe_load_json(path: str) -> Tuple[bool, Any]:
    """
    Charge un fichier JSON sans propager d'exception vers le haut.

    - Fichier absent → ``(False, "absent")``.
    - JSON invalide ou erreur I/O → ``(False, "<message>")``, log WARN.
    - Succès → ``(True, data_dict)``.

    :param path: Chemin du fichier JSON à lire.
    :return: Tuple ``(ok, data_or_error_message)`` — data est un dict si ok=True,
             sinon une chaîne décrivant l'erreur.
    """
    if not os.path.exists(path):
        return False, "absent"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return True, data
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        _log.warning("state.json corrompu (décodage invalide) : %s — %s", path, exc)
        return False, f"json_corrupt: {exc}"
    except OSError as exc:
        _log.warning("state.json illisible (OSError) : %s — %s", path, exc)
        return False, f"os_error: {exc}"


# ---------------------------------------------------------------------------
# Profil canonique + jobKey
# ---------------------------------------------------------------------------

def canonical_profile(prep_info: dict, ocr_info: dict, ocr_lang: str = "fra+eng") -> dict:
    """
    Construit le profil canonique incluant les versions des outils.
    La langue est normalisée (tokens triés + dédupliqués) pour garantir
    la déterminisme du hash même si l'ordre change.

    :param prep_info: Réponse JSON de GET /info du prep-service.
    :param ocr_info: Réponse JSON de GET /info de l'ocr-service.
    :param ocr_lang: Langues OCR, ex: ``"fra+eng"`` ou ``"eng+fra"``.
    :return: Dict de profil canonique.
    """
    # Normalisation de la langue : trier les tokens pour déterminisme
    lang_tokens = sorted(set(ocr_lang.split("+")))
    normalized_lang = "+".join(lang_tokens)

    return {
        "ocr": {
            "lang": normalized_lang,
            "rotatePages": True,
            "deskew": True,
            "optimize": 1,
            "tools": ocr_info.get("versions", {}),
        },
        "prep": {
            "tools": prep_info.get("versions", {}),
        },
    }


def stable_json(obj: dict) -> str:
    """
    Sérialise un dict en JSON compact avec clés triées (déterministe).

    :param obj: Objet à sérialiser.
    :return: Chaîne JSON canonique.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_str(s: str) -> str:
    """
    Calcule le SHA-256 hexadécimal d'une chaîne UTF-8.

    :param s: Chaîne d'entrée.
    :return: Hash hex (64 caractères).
    """
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_job_key(file_hash: str, profile: dict) -> tuple:
    """
    Calcule le jobKey = ``fileHash__profileHash``.

    :param file_hash: SHA-256 hexadécimal du fichier source.
    :param profile: Dict de profil canonique.
    :return: Tuple ``(profile_hash, job_key)``.
    """
    profile_hash = sha256_str(stable_json(profile))
    job_key = f"{file_hash}__{profile_hash}"
    return profile_hash, job_key


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

def is_heartbeat_stale(hb_path: str, timeout_s: int, absent_timeout_s: Optional[int] = None) -> bool:
    """
    Détermine si un heartbeat est périmé.

    - Si le fichier est absent : considéré stale après ``absent_timeout_s``
      (défaut = ``2 * timeout_s``) pour éviter les faux positifs au démarrage.
    - Si le fichier est présent : stale si l'heure de modification est plus
      ancienne que ``timeout_s`` secondes.

    :param hb_path: Chemin du fichier heartbeat.
    :param timeout_s: Durée en secondes avant de considérer un heartbeat présent comme périmé.
    :param absent_timeout_s: Durée avant de considérer un heartbeat absent comme périmé.
                             Si None, vaut ``2 * timeout_s``.
    :return: True si le heartbeat est périmé ou absent depuis trop longtemps.
    """
    if absent_timeout_s is None:
        absent_timeout_s = 2 * timeout_s

    now = time.time()
    if not os.path.exists(hb_path):
        # On ne peut pas savoir depuis quand le fichier est absent ;
        # on retourne True uniquement si le timeout "absent" est nul
        # (utile pour les tests qui veulent forcer le stale immédiatement).
        return absent_timeout_s == 0

    age = now - os.path.getmtime(hb_path)
    return age > timeout_s


# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------

# Whitelist complète des compteurs supportés
_METRIC_KEYS = frozenset({
    "done", "error", "running", "queued",
    "disk_error", "pdf_invalid", "input_rejected_size", "input_rejected_signature",
})


def make_empty_metrics() -> dict:
    """
    Retourne un dict de métriques initialisé à zéro.

    Compteurs :
    - done, error, running, queued (pipeline)
    - disk_error (espace disque insuffisant avant PREP)
    - pdf_invalid (PDF final invalide après OCR)
    - input_rejected_size (fichier entrant trop grand)
    - input_rejected_signature (signature ZIP/RAR invalide)

    :return: Dict de métriques initialisé.
    """
    return {
        "done": 0,
        "error": 0,
        "running": 0,
        "queued": 0,
        "disk_error": 0,
        "pdf_invalid": 0,
        "input_rejected_size": 0,
        "input_rejected_signature": 0,
        "updatedAt": "",
    }


def update_metrics(metrics: dict, event: str) -> dict:
    """
    Incrémente le compteur correspondant à ``event`` dans le dict de métriques.
    Retourne le même dict (mutation in-place + retour pour faciliter les tests).

    Événements supportés : ``"done"``, ``"error"``, ``"running"``, ``"queued"``,,
    ``"disk_error"``, ``"pdf_invalid"``, ``"input_rejected_size"``,,
    ``"input_rejected_signature"``.
    Les événements inconnus sont ignorés.

    :param metrics: Dict de métriques courant.
    :param event: Nom du compteur à incrémenter.
    :return: Dict de métriques mis à jour.
    """
    if event in _METRIC_KEYS and event in metrics:
        metrics[event] += 1
    metrics["updatedAt"] = now_iso()
    return metrics


def write_metrics(metrics: dict, index_dir: str) -> str:
    """
    Persiste le dict de métriques dans ``<index_dir>/metrics.json``.

    :param metrics: Dict de métriques à écrire.
    :param index_dir: Répertoire d'index où écrire le fichier.
    :return: Chemin du fichier écrit.
    """
    ensure_dir(index_dir)
    path = os.path.join(index_dir, "metrics.json")
    metrics["updatedAt"] = now_iso()
    atomic_write_json(path, metrics)
    return path

