"""
Tests unitaires du prep-service — tri naturel, filtrage images, génération PDF.
Aucun outil externe requis (7z non invoqué).
"""
import os
import sys

# Permettre l'import du package app depuis le dossier service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.core import filter_images, sort_images, images_to_pdf


# ---------------------------------------------------------------------------
# Tri naturel
# ---------------------------------------------------------------------------

class TestSortImages:
    """Vérifications du tri naturel des noms de fichiers."""

    def test_tri_numerique_basique(self, tmp_path):
        """Les fichiers sont triés par ordre numérique, pas lexicographique."""
        paths = [
            str(tmp_path / "10.jpg"),
            str(tmp_path / "2.jpg"),
            str(tmp_path / "1.jpg"),
        ]
        result = sort_images(paths)
        noms = [os.path.basename(p) for p in result]
        assert noms == ["1.jpg", "2.jpg", "10.jpg"]

    def test_tri_avec_zeros_initiaux(self, tmp_path):
        """Les zéros initiaux sont ignorés pour l'ordre (001 = 1)."""
        paths = [
            str(tmp_path / "003.png"),
            str(tmp_path / "001.png"),
            str(tmp_path / "010.png"),
            str(tmp_path / "002.png"),
        ]
        result = sort_images(paths)
        noms = [os.path.basename(p) for p in result]
        assert noms == ["001.png", "002.png", "003.png", "010.png"]

    def test_tri_insensible_a_la_casse(self, tmp_path):
        """Le tri est insensible à la casse (A avant b)."""
        paths = [
            str(tmp_path / "Page_B_01.jpg"),
            str(tmp_path / "page_a_02.jpg"),
            str(tmp_path / "Page_A_01.jpg"),
        ]
        result = sort_images(paths)
        noms = [os.path.basename(p) for p in result]
        # Tri naturel : page_a_01 < page_a_02 < page_b_01 (insensible à la casse)
        assert noms[0].lower() == "page_a_01.jpg"
        assert noms[1].lower() == "page_a_02.jpg"
        assert noms[2].lower() == "page_b_01.jpg"

    def test_liste_vide(self):
        """Une liste vide retourne une liste vide."""
        assert sort_images([]) == []


# ---------------------------------------------------------------------------
# Filtrage images
# ---------------------------------------------------------------------------

class TestFilterImages:
    """Vérifications du filtrage des fichiers images (parasites exclus)."""

    def test_seuls_les_formats_images_sont_retenus(self, tmp_path):
        """Seuls les fichiers avec extension image valide sont retournés."""
        (tmp_path / "page1.jpg").write_bytes(b"fake")
        (tmp_path / "page2.PNG").write_bytes(b"fake")
        (tmp_path / "page3.webp").write_bytes(b"fake")
        (tmp_path / "readme.txt").write_bytes(b"texte")
        (tmp_path / "data.xml").write_bytes(b"<xml/>")

        result = filter_images(str(tmp_path))
        noms = {os.path.basename(p) for p in result}
        assert "page1.jpg" in noms
        assert "page2.PNG" in noms
        assert "page3.webp" in noms
        assert "readme.txt" not in noms
        assert "data.xml" not in noms

    def test_exclusion_parasites(self, tmp_path):
        """Les fichiers parasites (thumbs.db, .DS_Store) sont exclus."""
        (tmp_path / "page1.jpg").write_bytes(b"fake")
        (tmp_path / "Thumbs.db").write_bytes(b"parasite")
        (tmp_path / ".DS_Store").write_bytes(b"parasite")
        (tmp_path / "desktop.ini").write_bytes(b"parasite")

        result = filter_images(str(tmp_path))
        noms = {os.path.basename(p) for p in result}
        assert "page1.jpg" in noms
        assert "Thumbs.db" not in noms
        assert ".DS_Store" not in noms
        assert "desktop.ini" not in noms

    def test_exclusion_dossier_macosx(self, tmp_path):
        """Le dossier __MACOSX (archives Mac) est entièrement ignoré."""
        macosx = tmp_path / "__MACOSX"
        macosx.mkdir()
        (macosx / "hidden.jpg").write_bytes(b"fake")
        (tmp_path / "real.jpg").write_bytes(b"fake")

        result = filter_images(str(tmp_path))
        chemins = {os.path.normpath(p) for p in result}
        assert not any("__macosx" in p.lower() for p in chemins)
        assert any("real.jpg" in p for p in chemins)

    def test_recursif_sous_dossiers(self, tmp_path):
        """Les images dans les sous-dossiers sont bien remontées."""
        sub = tmp_path / "chapitre1"
        sub.mkdir()
        (sub / "p01.jpg").write_bytes(b"fake")
        (tmp_path / "cover.jpg").write_bytes(b"fake")

        result = filter_images(str(tmp_path))
        assert len(result) == 2

    def test_dossier_vide(self, tmp_path):
        """Un dossier vide retourne une liste vide."""
        assert filter_images(str(tmp_path)) == []


# ---------------------------------------------------------------------------
# Smoke test génération PDF (sans 7z)
# ---------------------------------------------------------------------------

class TestImagesToPdf:
    """Smoke test de la génération PDF via img2pdf (sans 7z)."""

    def test_pdf_commence_par_signature(self, tmp_path):
        """Le PDF généré commence bien par la signature b'%PDF'."""
        pytest.importorskip("PIL", reason="pillow requis pour générer des images de test")
        from PIL import Image

        # Générer 2 petites images PNG de test
        img1_path = str(tmp_path / "p1.png")
        img2_path = str(tmp_path / "p2.png")
        for path in [img1_path, img2_path]:
            img = Image.new("RGB", (10, 10), color=(128, 0, 0))
            img.save(path)

        dest = str(tmp_path / "output.pdf")
        images_to_pdf([img1_path, img2_path], dest)

        assert os.path.exists(dest)
        with open(dest, "rb") as f:
            header = f.read(4)
        assert header == b"%PDF"

    def test_liste_vide_leve_valuerror(self, tmp_path):
        """Une liste d'images vide lève ValueError."""
        dest = str(tmp_path / "output.pdf")
        with pytest.raises(ValueError, match="vide"):
            images_to_pdf([], dest)

    def test_fichier_invalide_leve_exception(self, tmp_path):
        """Un fichier non-image lève une exception lors de la conversion."""
        bad_file = str(tmp_path / "not_an_image.jpg")
        with open(bad_file, "w") as f:
            f.write("ceci n'est pas une image")
        dest = str(tmp_path / "output.pdf")
        with pytest.raises(Exception):
            images_to_pdf([bad_file], dest)

