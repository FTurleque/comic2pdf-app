"""
Watch-folder local — surveille un dossier et lance le pipeline comic2pdf
sur chaque nouveau fichier CBZ/CBR détecté.

Usage :
    python tools/watch_local.py --in ./data/in --out ./data/out [options]

Options :
    --in  <dir>         Dossier d'entrée à surveiller (défaut: ./data/in)
    --out <dir>         Dossier de sortie des PDFs (défaut: ./data/out)
    --lang fra+eng      Langue(s) OCR (défaut: fra+eng)
    --no-ocr            Désactiver l'OCR
    --keep-temp         Conserver les dossiers de travail temporaires
    --poll-interval 2   Intervalle de polling en secondes (défaut: 2)
    --check-deps        Vérifier les dépendances et quitter
    --hold-dir <dir>    Dossier pour les doublons (défaut: ./data/hold/duplicates)
"""
import argparse
import json
import os
import shutil
import sys
import time

# Ajouter la racine du repo au path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.deps import MissingDepError, check_all_deps, check_deps_report
from tools.pipeline_core import (
    ensure_dir,
    sha256_file,
    make_job_key,
    output_filename,
    validate_pdf,
    check_file_signature,
    atomic_write_json,
    read_json,
    now_iso,
)
from tools.cli import run_pipeline

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_PROCESSED_DB = "processed.json"
_SUPPORTED_EXTS = {".cbz", ".cbr"}

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construit et retourne le parser argparse du watcher.

    :return: Instance ``ArgumentParser`` configurée.
    """
    p = argparse.ArgumentParser(
        prog="watch_local",
        description="Surveille un dossier et convertit chaque CBZ/CBR en PDF.",
    )
    p.add_argument("--in",  dest="in_dir",  default="./data/in",
                   metavar="DIR", help="Dossier d'entrée à surveiller.")
    p.add_argument("--out", dest="out_dir", default="./data/out",
                   metavar="DIR", help="Dossier de sortie des PDFs.")
    p.add_argument("--lang",          default="fra+eng",
                   metavar="LANG",    help="Langue(s) OCR (défaut: fra+eng).")
    p.add_argument("--no-ocr",        action="store_true",
                   help="Désactiver l'OCR.")
    p.add_argument("--keep-temp",     action="store_true",
                   help="Conserver les dossiers de travail temporaires.")
    p.add_argument("--poll-interval", type=float, default=2.0,
                   metavar="SEC",     help="Intervalle de polling en secondes (défaut: 2).")
    p.add_argument("--check-deps",    action="store_true",
                   help="Vérifier les dépendances et quitter.")
    p.add_argument("--hold-dir", dest="hold_dir",
                   default="./data/hold/duplicates",
                   metavar="DIR", help="Dossier pour les doublons.")
    return p

# ---------------------------------------------------------------------------
# État persisté (processed.json)
# ---------------------------------------------------------------------------

def load_processed(db_path: str) -> dict:
    """Charge la base des fichiers déjà traités.

    :param db_path: Chemin du fichier JSON de base.
    :return: Dict ``{job_key: {fileName, processedAt, outputPdf}}``.
    """
    data = read_json(db_path)
    return data if isinstance(data, dict) else {}


def save_processed(db_path: str, state: dict) -> None:
    """Persiste la base des fichiers traités de manière atomique.

    :param db_path: Chemin du fichier JSON de base.
    :param state: Dict d'état à sauvegarder.
    """
    atomic_write_json(db_path, state)

# ---------------------------------------------------------------------------
# Détection des fichiers entrants
# ---------------------------------------------------------------------------

def scan_for_new_files(in_dir: str) -> list:
    """Retourne la liste des fichiers CBZ/CBR dans ``in_dir``.

    Ignore les fichiers ``.part`` (en cours de copie).

    :param in_dir: Dossier à scanner.
    :return: Liste de chemins absolus.
    """
    result = []
    try:
        for fn in os.listdir(in_dir):
            ext = os.path.splitext(fn)[1].lower()
            if ext in _SUPPORTED_EXTS:
                result.append(os.path.join(in_dir, fn))
    except FileNotFoundError:
        pass
    return result

# ---------------------------------------------------------------------------
# Gestion des doublons
# ---------------------------------------------------------------------------

def handle_duplicate(
    input_path: str,
    job_key: str,
    existing: dict,
    hold_dir: str,
) -> None:
    """Déplace le fichier entrant dans ``hold_dir`` et journalise le doublon.

    :param input_path: Chemin du fichier entrant.
    :param job_key: Clé du job (doublon détecté).
    :param existing: Entrée existante dans la base.
    :param hold_dir: Dossier de hold pour les doublons.
    """
    dest_dir = os.path.join(hold_dir, job_key)
    ensure_dir(dest_dir)
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    hold_name = f"{ts}__{os.path.basename(input_path)}"
    hold_path = os.path.join(dest_dir, hold_name)
    shutil.move(input_path, hold_path)
    print(
        f"[watch_local] DOUBLON détecté : '{os.path.basename(input_path)}'\n"
        f"  jobKey   : {job_key}\n"
        f"  Existant : {existing.get('outputPdf', '?')}\n"
        f"  Fichier déplacé vers : {hold_path}\n"
        f"  Pour forcer le retraitement, supprimer l'entrée de hold/ et relancer."
    )

# ---------------------------------------------------------------------------
# Traitement d'un fichier
# ---------------------------------------------------------------------------

def process_file(
    input_path: str,
    out_dir: str,
    lang: str,
    no_ocr: bool,
    keep_temp: bool,
    hold_dir: str,
    processed: dict,
    db_path: str,
) -> None:
    """Traite un fichier CBZ/CBR : vérification doublon, pipeline, persistance.

    :param input_path: Chemin du fichier à traiter.
    :param out_dir: Dossier de sortie.
    :param lang: Langue(s) OCR.
    :param no_ocr: Désactiver l'OCR.
    :param keep_temp: Conserver les dossiers temporaires.
    :param hold_dir: Dossier pour les doublons.
    :param processed: Dict d'état chargé en mémoire.
    :param db_path: Chemin du fichier processed.json.
    """
    fname = os.path.basename(input_path)

    # Vérification signature (fichier corrompu → ignorer)
    if not check_file_signature(input_path):
        print(f"[watch_local] IGNORÉ (signature invalide) : {fname}")
        return

    # Calcul du jobKey
    try:
        file_hash = sha256_file(input_path)
    except Exception as e:
        print(f"[watch_local] ERREUR (sha256) : {fname} — {e}")
        return

    _, job_key = make_job_key(file_hash, lang)

    # Doublon ?
    if job_key in processed:
        handle_duplicate(input_path, job_key, processed[job_key], hold_dir)
        return

    # Pipeline
    print(f"[watch_local] Traitement : {fname} (jobKey={job_key[:16]}...)")
    try:
        final_pdf = run_pipeline(
            input_path=input_path,
            out_dir=out_dir,
            lang=lang,
            no_ocr=no_ocr,
            keep_temp=keep_temp,
        )
        # Marquer comme traité
        processed[job_key] = {
            "fileName":   fname,
            "jobKey":     job_key,
            "processedAt": now_iso(),
            "outputPdf":  final_pdf,
        }
        save_processed(db_path, processed)
        print(f"[watch_local] ✓ Terminé : {fname}")
    except SystemExit as e:
        print(f"[watch_local] ERREUR : {fname} — pipeline terminé avec code {e}")
    except Exception as e:
        print(f"[watch_local] ERREUR inattendue : {fname} — {e}")

# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------

def watch_loop(
    in_dir: str,
    out_dir: str,
    lang: str,
    no_ocr: bool,
    keep_temp: bool,
    poll_interval: float,
    hold_dir: str,
    *,
    stop_after: int = 0,
) -> None:
    """Boucle de surveillance (polling) du dossier d'entrée.

    :param in_dir: Dossier à surveiller.
    :param out_dir: Dossier de sortie des PDFs.
    :param lang: Langue(s) OCR.
    :param no_ocr: Désactiver l'OCR.
    :param keep_temp: Conserver les dossiers temporaires.
    :param poll_interval: Intervalle de polling en secondes.
    :param hold_dir: Dossier pour les doublons.
    :param stop_after: Si > 0, arrête après N itérations (test uniquement).
    """
    ensure_dir(in_dir)
    ensure_dir(out_dir)
    ensure_dir(hold_dir)

    db_path = os.path.join(out_dir, _PROCESSED_DB)
    processed = load_processed(db_path)

    print(f"[watch_local] Surveillance de '{in_dir}' (intervalle={poll_interval}s).")
    print(f"[watch_local] PDFs → '{out_dir}' | doublons → '{hold_dir}'")
    print("[watch_local] Appuyer sur Ctrl+C pour arrêter.\n")

    iteration = 0
    try:
        while True:
            iteration += 1
            files = scan_for_new_files(in_dir)
            for fpath in files:
                process_file(
                    input_path=fpath,
                    out_dir=out_dir,
                    lang=lang,
                    no_ocr=no_ocr,
                    keep_temp=keep_temp,
                    hold_dir=hold_dir,
                    processed=processed,
                    db_path=db_path,
                )
            if stop_after and iteration >= stop_after:
                break
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n[watch_local] Arrêt demandé. À bientôt !")

# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main(argv: list = None) -> int:
    """Point d'entrée principal du watcher.

    :param argv: Arguments CLI (défaut: sys.argv[1:]).
    :return: Code de sortie (0 = succès, 1 = erreur).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.check_deps:
        print(check_deps_report(no_ocr=args.no_ocr))
        return 0

    # Vérification des dépendances
    try:
        check_all_deps(no_ocr=args.no_ocr)
    except MissingDepError as e:
        print(f"[watch_local] ERREUR — dépendance manquante :\n{e}", file=sys.stderr)
        return 1

    watch_loop(
        in_dir=os.path.abspath(args.in_dir),
        out_dir=os.path.abspath(args.out_dir),
        lang=args.lang,
        no_ocr=args.no_ocr,
        keep_temp=args.keep_temp,
        poll_interval=args.poll_interval,
        hold_dir=os.path.abspath(args.hold_dir),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

