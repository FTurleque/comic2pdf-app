"""
CLI comic2pdf — conversion ponctuelle CBZ/CBR → PDF avec texte sélectionnable.

Usage :
    python tools/cli.py <input.cbz|cbr> [options]

Options :
    --lang fra+eng   Langue(s) OCR Tesseract (défaut : fra+eng)
    --out <dir>      Dossier de sortie (défaut : répertoire courant)
    --no-ocr         Produire uniquement le raw.pdf sans OCR
    --keep-temp      Conserver le dossier de travail temporaire
    --check-deps     Vérifier les dépendances et quitter
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from tqdm import tqdm

# Ajouter la racine du repo au path pour importer tools/
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.deps import (
    MissingDepError,
    check_deps_report,
    check_all_deps,
    require_tool,
)
from tools.pipeline_core import (
    ensure_dir,
    sha256_file,
    make_job_key,
    output_filename,
    list_and_sort_images,
    images_to_pdf,
    build_ocrmypdf_cmd,
    validate_pdf,
    check_file_signature,
    ZipSlipError,
    safe_replace,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1

# ---------------------------------------------------------------------------
# Parsing des arguments
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construit et retourne le parser argparse du CLI.

    :return: Instance ``ArgumentParser`` configurée.
    """
    p = argparse.ArgumentParser(
        prog="comic2pdf",
        description="Convertit un fichier CBZ/CBR en PDF avec texte sélectionnable (OCR).",
    )
    p.add_argument(
        "input",
        nargs="?",
        help="Fichier CBZ ou CBR à convertir.",
    )
    p.add_argument(
        "--lang",
        default="fra+eng",
        metavar="LANG",
        help="Langue(s) Tesseract, ex: fra+eng (défaut: fra+eng).",
    )
    p.add_argument(
        "--out",
        default=".",
        metavar="DIR",
        help="Dossier de sortie (défaut: répertoire courant).",
    )
    p.add_argument(
        "--no-ocr",
        action="store_true",
        help="Ne pas effectuer l'OCR — produire uniquement le raw.pdf.",
    )
    p.add_argument(
        "--keep-temp",
        action="store_true",
        help="Conserver le dossier de travail temporaire après la conversion.",
    )
    p.add_argument(
        "--check-deps",
        action="store_true",
        help="Vérifier les dépendances externes et quitter.",
    )
    return p


def validate_input(input_path: str) -> None:
    """Valide le fichier d'entrée : existence, extension, signature.

    :param input_path: Chemin du fichier source.
    :raises SystemExit: Si le fichier est invalide.
    """
    if not os.path.isfile(input_path):
        _die(f"Fichier introuvable : {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in {".cbz", ".cbr"}:
        _die(f"Extension non supportée : '{ext}'. Seuls .cbz et .cbr sont acceptés.")

    if not check_file_signature(input_path):
        _die(
            f"Signature de fichier invalide : '{input_path}' ne ressemble ni à un ZIP ni à un RAR.\n"
            "Vérifiez que le fichier n'est pas corrompu."
        )


# ---------------------------------------------------------------------------
# Pipeline local
# ---------------------------------------------------------------------------

def run_pipeline(
    input_path: str,
    out_dir: str,
    lang: str,
    no_ocr: bool,
    keep_temp: bool,
) -> str:
    """Exécute le pipeline complet : extraction → raw.pdf → (OCR →) final.pdf.

    :param input_path: Chemin absolu du fichier CBZ/CBR source.
    :param out_dir: Dossier de sortie pour le PDF final.
    :param lang: Langue(s) OCR.
    :param no_ocr: Si True, s'arrête après le raw.pdf.
    :param keep_temp: Si True, ne supprime pas le dossier de travail.
    :return: Chemin absolu du PDF produit.
    :raises SystemExit: En cas d'erreur de pipeline.
    """
    input_path = os.path.abspath(input_path)
    ensure_dir(out_dir)

    # Calcul du jobKey (pour le nommage du fichier de sortie)
    print(f"[comic2pdf] Calcul de l'empreinte SHA-256 de '{os.path.basename(input_path)}'...")
    file_hash = sha256_file(input_path)
    _, job_key = make_job_key(file_hash, lang)
    out_name = output_filename(input_path, job_key)
    final_pdf = os.path.join(out_dir, out_name)

    if os.path.isfile(final_pdf):
        print(f"[comic2pdf] PDF déjà produit : {final_pdf}")
        return final_pdf

    # Créer un dossier de travail temporaire
    work_dir = tempfile.mkdtemp(prefix=f"comic2pdf_{job_key[:8]}_")
    pages_dir = os.path.join(work_dir, "pages")
    raw_pdf   = os.path.join(work_dir, "raw.pdf")

    try:
        # --- Étape 1 : extraction 7z ---
        _step_extract(input_path, pages_dir)

        # --- Étape 2 : images → raw.pdf ---
        _step_images_to_pdf(pages_dir, raw_pdf)

        # --- Étape 3 : OCR ---
        if no_ocr:
            _copy_atomic(raw_pdf, final_pdf)
            print(f"[comic2pdf] (--no-ocr) raw.pdf copié → {final_pdf}")
        else:
            _step_ocr(raw_pdf, final_pdf, lang)

        print(f"[comic2pdf] ✓ PDF produit : {final_pdf}")
        return final_pdf

    except SystemExit:
        raise
    except Exception as exc:
        _die(f"Erreur inattendue : {exc}")
    finally:
        if not keep_temp:
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            print(f"[comic2pdf] Dossier de travail conservé : {work_dir}")

    # Jamais atteint (pour mypy)
    raise SystemExit(EXIT_ERR)  # pragma: no cover


def _step_extract(input_path: str, pages_dir: str) -> None:
    """Extrait l'archive CBZ/CBR dans ``pages_dir`` via 7z.

    :param input_path: Chemin de l'archive.
    :param pages_dir: Dossier de destination de l'extraction.
    :raises SystemExit: Si 7z échoue.
    """
    ensure_dir(pages_dir)
    sz = require_tool("7z")
    cmd = [sz, "x", "-y", f"-o{pages_dir}", input_path]

    print(f"[comic2pdf] Extraction : {os.path.basename(input_path)}")
    with tqdm(desc="Extraction 7z", unit="fichier", bar_format="{desc}: {bar} {n_fmt}") as pbar:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        pbar.update(1)

    if result.returncode != 0:
        _die(
            f"7z a échoué (code {result.returncode}) :\n"
            f"{result.stderr or result.stdout}"
        )


def _step_images_to_pdf(pages_dir: str, raw_pdf: str) -> None:
    """Convertit les images extraites en raw.pdf.

    :param pages_dir: Dossier contenant les images extraites.
    :param raw_pdf: Chemin de destination du raw.pdf.
    :raises SystemExit: Si aucune image n'est trouvée ou si img2pdf échoue.
    """
    try:
        images = list_and_sort_images(pages_dir)
    except ZipSlipError as e:
        _die(f"Sécurité zip-slip : {e}")
        return  # pragma: no cover

    if not images:
        _die("Aucune image trouvée dans l'archive. Le fichier est peut-être corrompu.")

    print(f"[comic2pdf] Génération raw.pdf ({len(images)} page(s))...")
    with tqdm(total=len(images), desc="Conversion images→PDF", unit="page") as pbar:
        try:
            images_to_pdf(images, raw_pdf)
            pbar.update(len(images))
        except ImportError as e:
            _die(f"img2pdf manquant : {e}\n  → pip install img2pdf")
        except Exception as e:
            _die(f"Échec de la génération du raw.pdf : {e}")


def _step_ocr(raw_pdf: str, final_pdf: str, lang: str) -> None:
    """Applique l'OCR sur ``raw_pdf`` et produit ``final_pdf``.

    :param raw_pdf: Chemin du PDF source (sans OCR).
    :param final_pdf: Chemin de destination du PDF final (avec OCR).
    :param lang: Langue(s) Tesseract.
    :raises SystemExit: Si ocrmypdf est absent ou échoue.
    """
    ocr_bin = require_tool("ocrmypdf")
    tmp_pdf = final_pdf + ".tmp"
    cmd = build_ocrmypdf_cmd(raw_pdf, tmp_pdf, lang=lang)
    # Remplacer "ocrmypdf" par le chemin résolu
    cmd[0] = ocr_bin

    print(f"[comic2pdf] OCR en cours (lang={lang})...")
    with tqdm(desc="OCR Tesseract", unit="étape", bar_format="{desc}: {bar}") as pbar:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        pbar.update(1)

    if result.returncode != 0:
        _die(
            f"ocrmypdf a échoué (code {result.returncode}) :\n"
            f"{result.stderr or result.stdout}"
        )

    if not validate_pdf(tmp_pdf):
        try:
            os.remove(tmp_pdf)
        except FileNotFoundError:
            pass
        _die("Le PDF produit par ocrmypdf est invalide ou trop petit.")

    safe_replace(tmp_pdf, final_pdf)


def _copy_atomic(src: str, dst: str) -> None:
    """Copie ``src`` vers ``dst`` de manière atomique (tmp + rename).

    Utilise :func:`safe_replace` pour couvrir le cas cross-device sur Windows.

    :param src: Chemin source.
    :param dst: Chemin de destination.
    """
    tmp = dst + ".tmp"
    shutil.copy2(src, tmp)
    safe_replace(tmp, dst)


def _die(message: str, code: int = EXIT_ERR) -> None:
    """Affiche un message d'erreur sur stderr et termine le processus.

    :param message: Message d'erreur.
    :param code: Code de sortie (défaut : 1).
    """
    print(f"[comic2pdf] ERREUR : {message}", file=sys.stderr)
    sys.exit(code)

# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main(argv: list = None) -> int:
    """Point d'entrée principal du CLI.

    :param argv: Arguments CLI (défaut : sys.argv[1:]).
    :return: Code de sortie (0 = succès, 1 = erreur).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # --check-deps : rapport de dépendances et sortie
    if args.check_deps:
        print(check_deps_report(no_ocr=getattr(args, "no_ocr", False)))
        return EXIT_OK

    # Vérification : fichier input obligatoire
    if not args.input:
        parser.print_help()
        return EXIT_ERR

    # Vérification des dépendances avant tout traitement
    try:
        check_all_deps(no_ocr=args.no_ocr)
    except MissingDepError as e:
        print(f"[comic2pdf] ERREUR — dépendance manquante :\n{e}", file=sys.stderr)
        return EXIT_ERR

    # Validation du fichier d'entrée
    try:
        validate_input(args.input)
    except SystemExit as e:
        return int(str(e)) if str(e).isdigit() else EXIT_ERR

    # Exécution du pipeline
    try:
        run_pipeline(
            input_path=args.input,
            out_dir=args.out,
            lang=args.lang,
            no_ocr=args.no_ocr,
            keep_temp=args.keep_temp,
        )
        return EXIT_OK
    except SystemExit as e:
        return int(str(e)) if str(e).isdigit() else EXIT_ERR


if __name__ == "__main__":
    sys.exit(main())

