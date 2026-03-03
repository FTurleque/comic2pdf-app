#!/usr/bin/env python3
"""
Script de démonstration des fonctionnalités de robustesse FS.
Utilise les fonctions de app/utils.py pour valider leur comportement.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils import (
    validate_pdf,
    check_disk_space,
    check_input_size,
    check_file_signature,
    cleanup_old_workdirs,
)


def demo_validate_pdf():
    """Démo : validation de PDFs."""
    print("\n=== Démonstration validate_pdf() ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # PDF valide
        valid_pdf = Path(tmpdir) / "valid.pdf"
        valid_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2048)
        print(f"✅ PDF valide : {validate_pdf(str(valid_pdf))}")

        # PDF invalide (pas de header)
        invalid_pdf = Path(tmpdir) / "invalid.pdf"
        invalid_pdf.write_bytes(b"NOT A PDF\n" + b"x" * 2048)
        print(f"❌ PDF invalide : {validate_pdf(str(invalid_pdf))}")

        # PDF trop petit
        tiny_pdf = Path(tmpdir) / "tiny.pdf"
        tiny_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 10)
        print(f"❌ PDF trop petit (< 1024 octets) : {validate_pdf(str(tiny_pdf))}")

        # Fichier inexistant
        print(f"❌ Fichier inexistant : {validate_pdf('/tmp/absent.pdf')}")


def demo_check_disk_space():
    """Démo : vérification espace disque."""
    print("\n=== Démonstration check_disk_space() ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Fichier de 1 Mo avec factor=2.0 (besoin de 2 Mo)
        result = check_disk_space(tmpdir, 1024 * 1024, factor=2.0)
        print(f"✅ Espace suffisant pour 1 Mo (× 2.0) : {result}")

        # Afficher l'espace réel disponible
        usage = shutil.disk_usage(tmpdir)
        free_gb = usage.free / (1024 ** 3)
        print(f"   Espace libre : {free_gb:.2f} Go")


def demo_check_input_size():
    """Démo : vérification taille fichier."""
    print("\n=== Démonstration check_input_size() ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Fichier de 1 Mo (OK pour max_mb=500)
        small_file = Path(tmpdir) / "small.cbz"
        small_file.write_bytes(b"x" * (1024 * 1024))  # 1 Mo
        print(f"✅ Fichier 1 Mo (max 500 Mo) : {check_input_size(str(small_file), max_mb=500)}")

        # Simuler un gros fichier (fichier réel de 1 Mo, mais on vérifie avec max=0.5 Mo)
        print(f"❌ Fichier 1 Mo (max 0.5 Mo) : {check_input_size(str(small_file), max_mb=0.5)}")


def demo_check_file_signature():
    """Démo : vérification signature ZIP/RAR."""
    print("\n=== Démonstration check_file_signature() ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Fichier ZIP (CBZ)
        zip_file = Path(tmpdir) / "comic.cbz"
        zip_file.write_bytes(b"\x50\x4B\x03\x04" + b"\x00" * 100)
        print(f"✅ Signature ZIP : {check_file_signature(str(zip_file))}")

        # Fichier RAR4 (CBR)
        rar4_file = Path(tmpdir) / "comic_rar4.cbr"
        rar4_file.write_bytes(b"\x52\x61\x72\x21\x1A\x07\x00" + b"\x00" * 100)
        print(f"✅ Signature RAR4 : {check_file_signature(str(rar4_file))}")

        # Fichier RAR5 (CBR)
        rar5_file = Path(tmpdir) / "comic_rar5.cbr"
        rar5_file.write_bytes(b"\x52\x61\x72\x21\x1A\x07\x01\x00" + b"\x00" * 100)
        print(f"✅ Signature RAR5 : {check_file_signature(str(rar5_file))}")

        # Fichier texte (invalide)
        text_file = Path(tmpdir) / "fake.cbz"
        text_file.write_bytes(b"This is not a comic archive!\n")
        print(f"❌ Fichier texte : {check_file_signature(str(text_file))}")


def demo_cleanup_old_workdirs():
    """Démo : nettoyage des workdirs anciens."""
    print("\n=== Démonstration cleanup_old_workdirs() ===")

    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        # Créer des dossiers de différentes anciennetés
        recent_dir = Path(tmpdir) / "job_recent"
        recent_dir.mkdir()
        print(f"Créé : {recent_dir.name} (récent)")

        old_dir = Path(tmpdir) / "job_old"
        old_dir.mkdir()
        # Modifier le mtime pour simuler un dossier vieux de 10 jours
        old_time = time.time() - (10 * 86400)
        os.utime(str(old_dir), (old_time, old_time))
        print(f"Créé : {old_dir.name} (vieux de 10 jours)")

        running_dir = Path(tmpdir) / "job_running_old"
        running_dir.mkdir()
        os.utime(str(running_dir), (old_time, old_time))
        print(f"Créé : {running_dir.name} (vieux mais en cours)")

        staging_dir = Path(tmpdir) / "_staging"
        staging_dir.mkdir()
        os.utime(str(staging_dir), (old_time, old_time))
        print(f"Créé : {staging_dir.name} (système, commence par _)")

        # Nettoyer les dossiers de plus de 7 jours
        print("\nNettoyage (keep_days=7, running={job_running_old})...")
        deleted = cleanup_old_workdirs(
            str(tmpdir),
            keep_days=7,
            running_job_keys={"job_running_old"}
        )

        print(f"\n✅ Dossiers supprimés : {deleted}")
        print(f"   Reste : {[d.name for d in Path(tmpdir).iterdir()]}")
        print(f"   - job_recent : conservé (récent)")
        print(f"   - job_running_old : conservé (en cours)")
        print(f"   - _staging : conservé (système)")
        print(f"   - job_old : SUPPRIMÉ (> 7 jours)")


def main():
    """Lance toutes les démonstrations."""
    print("="*70)
    print("DÉMONSTRATION — Fonctionnalités de robustesse FS")
    print("="*70)

    try:
        demo_validate_pdf()
        demo_check_disk_space()
        demo_check_input_size()
        demo_check_file_signature()
        demo_cleanup_old_workdirs()

        print("\n" + "="*70)
        print("✅ Toutes les démonstrations réussies !")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

