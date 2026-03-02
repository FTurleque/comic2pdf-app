"""
Générateur d'un CBZ minimal pour les tests E2E.

Crée une archive CBZ (= ZIP) contenant une seule image PNG 100×100 pixels.
Utilise uniquement Pillow + zipfile (stdlib) — aucun outil système requis.

Usage :
  python make_test_cbz.py [output_path]
  Défaut : test_minimal.cbz dans le répertoire courant
"""
import io
import os
import struct
import sys
import zipfile


def make_minimal_png(width: int = 100, height: int = 100) -> bytes:
    """
    Génère un PNG minimal valide (100×100, RGB bleu uniforme).
    Utilise Pillow si disponible, sinon génère un PNG synthétique.

    :param width: Largeur en pixels.
    :param height: Hauteur en pixels.
    :return: Bytes du fichier PNG.
    """
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height), color=(50, 100, 200))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback : PNG synthétique sans Pillow (1×1 pixel)
        return _make_1x1_png()


def _make_1x1_png() -> bytes:
    """Génère un PNG 1×1 pixel rouge sans Pillow (bytes hardcodés)."""
    import zlib
    import struct

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xFF\x00\x00")  # filtre 0 + pixel RGB rouge
    idat = chunk(b"IDAT", raw)
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def make_test_cbz(output_path: str = "test_minimal.cbz", num_pages: int = 2) -> str:
    """
    Crée un CBZ (ZIP) de test avec ``num_pages`` images PNG.

    :param output_path: Chemin du fichier CBZ à créer.
    :param num_pages: Nombre d'images à inclure (défaut : 2).
    :return: Chemin absolu du fichier créé.
    """
    png_data = make_minimal_png()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, num_pages + 1):
            zf.writestr(f"{i:03d}.png", png_data)
    return os.path.abspath(output_path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "test_minimal.cbz"
    path = make_test_cbz(out)
    print(f"CBZ créé : {path}")

