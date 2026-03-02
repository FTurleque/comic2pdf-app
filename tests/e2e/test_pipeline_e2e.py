"""
Test E2E : pipeline CBZ → PDF via Docker Compose.

Scénario :
  1. Générer un CBZ minimal (2 pages PNG 100×100)
  2. Déposer dans data/in/ via convention .part → rename (atomique)
  3. Attendre l'apparition d'un PDF dans data/out/ (poll toutes les 2s)
  4. Vérifier : taille > 0 + header %PDF-

Prérequis :
  - docker compose up -d doit être déjà lancé
  - data/ doit exister et être monté par les services

Variables d'environnement :
  DATA_DIR : chemin du dossier data/ (défaut : ./data relatif au repo)
  E2E_TIMEOUT : timeout total en secondes (défaut : 120)
  E2E_POLL_INTERVAL : intervalle de poll en secondes (défaut : 2)

Usage autonome (depuis la racine du repo) :
  python tests/e2e/test_pipeline_e2e.py

Usage pytest (CI) :
  pytest tests/e2e/test_pipeline_e2e.py -v
"""
import os
import shutil
import sys
import time

# Ajouter le dossier e2e dans le path pour make_test_cbz
sys.path.insert(0, os.path.dirname(__file__))
from make_test_cbz import make_test_cbz


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(REPO_ROOT, "data"))
IN_DIR = os.path.join(DATA_DIR, "in")
OUT_DIR = os.path.join(DATA_DIR, "out")

E2E_TIMEOUT = int(os.environ.get("E2E_TIMEOUT", "120"))
E2E_POLL_INTERVAL = float(os.environ.get("E2E_POLL_INTERVAL", "2"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deposit_cbz(cbz_path: str, filename: str) -> str:
    """
    Dépose un CBZ dans data/in/ via convention .part → rename.

    :param cbz_path: Chemin du CBZ source.
    :param filename: Nom du fichier cible dans data/in/.
    :return: Chemin final dans data/in/.
    """
    os.makedirs(IN_DIR, exist_ok=True)
    part_path = os.path.join(IN_DIR, filename + ".part")
    fin_path = os.path.join(IN_DIR, filename)
    shutil.copy2(cbz_path, part_path)
    os.replace(part_path, fin_path)
    return fin_path


def wait_for_pdf(base_name: str, timeout: float, poll: float) -> str:
    """
    Attend l'apparition d'un PDF dans data/out/ correspondant au fichier déposé.

    :param base_name: Nom sans extension du fichier source (ex: "e2e_test").
    :param timeout: Timeout en secondes.
    :param poll: Intervalle de polling en secondes.
    :return: Chemin du PDF trouvé.
    :raises TimeoutError: Si aucun PDF n'est trouvé dans le délai imparti.
    """
    deadline = time.time() + timeout
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"[E2E] Attente d'un PDF pour '{base_name}' dans {OUT_DIR} (timeout={timeout}s)...")
    while time.time() < deadline:
        for fname in os.listdir(OUT_DIR):
            if fname.lower().endswith(".pdf") and base_name.lower() in fname.lower():
                pdf_path = os.path.join(OUT_DIR, fname)
                print(f"[E2E] PDF trouvé : {fname}")
                return pdf_path
        remaining = deadline - time.time()
        print(f"[E2E] En attente... ({remaining:.0f}s restantes)")
        time.sleep(poll)
    raise TimeoutError(
        f"[E2E] ECHEC : Aucun PDF pour '{base_name}' dans data/out/ après {timeout}s\n"
        f"Contenu de data/out/ : {os.listdir(OUT_DIR) if os.path.exists(OUT_DIR) else '(dossier absent)'}"
    )


def verify_pdf(pdf_path: str) -> None:
    """
    Vérifie qu'un fichier est un PDF valide : taille > 0 et header %PDF-.

    :param pdf_path: Chemin du fichier PDF à vérifier.
    :raises AssertionError: Si le fichier est invalide.
    """
    assert os.path.exists(pdf_path), f"PDF introuvable : {pdf_path}"
    size = os.path.getsize(pdf_path)
    assert size > 0, f"PDF vide (taille=0) : {pdf_path}"
    with open(pdf_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", (
        f"Header PDF invalide dans {pdf_path} : {header!r} (attendu b'%PDF-')"
    )
    print(f"[E2E] ✅ PDF valide : {os.path.basename(pdf_path)} ({size} bytes)")


# ---------------------------------------------------------------------------
# Test E2E principal
# ---------------------------------------------------------------------------

def run_e2e_test() -> None:
    """
    Exécute le test E2E complet : dépôt → attente → vérification.

    :raises TimeoutError: Si le PDF n'apparaît pas dans le délai imparti.
    :raises AssertionError: Si le PDF est invalide.
    """
    cbz_name = "e2e_comic_test.cbz"
    base_name = "e2e_comic_test"

    # Générer un CBZ minimal
    tmp_cbz = os.path.join(REPO_ROOT, "tests", "e2e", "_tmp_e2e_test.cbz")
    try:
        make_test_cbz(tmp_cbz, num_pages=2)
        print(f"[E2E] CBZ généré : {tmp_cbz} ({os.path.getsize(tmp_cbz)} bytes)")

        # Déposer dans data/in/
        deposited = deposit_cbz(tmp_cbz, cbz_name)
        print(f"[E2E] Déposé : {deposited}")

        # Attendre le PDF
        pdf_path = wait_for_pdf(base_name, timeout=E2E_TIMEOUT, poll=E2E_POLL_INTERVAL)

        # Vérifier
        verify_pdf(pdf_path)
        print(f"[E2E] ✅ TEST E2E SUCCÈS")

    finally:
        # Nettoyage du CBZ temporaire
        try:
            os.remove(tmp_cbz)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Point d'entrée pytest
# ---------------------------------------------------------------------------

def test_pipeline_cbz_to_pdf() -> None:
    """
    Test E2E pytest : dépose un CBZ dans data/in/, attend le PDF dans data/out/.

    Ce test nécessite que `docker compose up -d` soit déjà lancé.
    Déclenché uniquement via workflow_dispatch ou label PR 'run-e2e' en CI.
    """
    run_e2e_test()


if __name__ == "__main__":
    print(f"[E2E] DATA_DIR={DATA_DIR}")
    print(f"[E2E] Timeout={E2E_TIMEOUT}s, Poll={E2E_POLL_INTERVAL}s")
    try:
        run_e2e_test()
        sys.exit(0)
    except (TimeoutError, AssertionError) as e:
        print(f"\n[E2E] ❌ ECHEC : {e}")
        sys.exit(1)

