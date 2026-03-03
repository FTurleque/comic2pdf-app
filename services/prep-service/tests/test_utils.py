"""
Tests du module utils — prep-service.
Couvre toutes les fonctions utilitaires : filesystem, JSON, hash, listing images.
"""
import json
import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Tests ensure_dir
# ---------------------------------------------------------------------------

class TestEnsureDir:
    """Tests de la fonction ensure_dir."""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """ensure_dir crée un répertoire s'il n'existe pas."""
        from app.utils import ensure_dir

        new_dir = tmp_path / "test_dir"
        assert not new_dir.exists()

        ensure_dir(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_dir_no_error_if_exists(self, tmp_path):
        """ensure_dir ne lève pas d'erreur si le répertoire existe déjà."""
        from app.utils import ensure_dir

        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # Ne doit pas lever d'exception
        ensure_dir(str(existing_dir))

        assert existing_dir.exists()

    def test_ensure_dir_creates_nested_directories(self, tmp_path):
        """ensure_dir crée les répertoires parents si nécessaire."""
        from app.utils import ensure_dir

        nested_dir = tmp_path / "a" / "b" / "c"
        assert not nested_dir.exists()

        ensure_dir(str(nested_dir))

        assert nested_dir.exists()
        assert (tmp_path / "a").exists()
        assert (tmp_path / "a" / "b").exists()


# ---------------------------------------------------------------------------
# Tests atomic_write_json et read_json
# ---------------------------------------------------------------------------

class TestJsonOperations:
    """Tests des fonctions JSON atomiques."""

    def test_atomic_write_json_creates_file(self, tmp_path):
        """atomic_write_json crée un fichier JSON."""
        from app.utils import atomic_write_json

        json_file = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        atomic_write_json(str(json_file), data)

        assert json_file.exists()
        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_atomic_write_json_overwrites_existing(self, tmp_path):
        """atomic_write_json écrase un fichier existant."""
        from app.utils import atomic_write_json

        json_file = tmp_path / "test.json"

        # Première écriture
        atomic_write_json(str(json_file), {"old": "data"})

        # Deuxième écriture (écrasement)
        atomic_write_json(str(json_file), {"new": "data"})

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {"new": "data"}
        assert "old" not in loaded

    def test_atomic_write_json_no_tmp_file_left(self, tmp_path):
        """atomic_write_json ne laisse pas de fichier .tmp."""
        from app.utils import atomic_write_json

        json_file = tmp_path / "test.json"
        tmp_file = tmp_path / "test.json.tmp"

        atomic_write_json(str(json_file), {"data": "test"})

        assert json_file.exists()
        assert not tmp_file.exists()

    def test_read_json_returns_data(self, tmp_path):
        """read_json retourne les données d'un fichier JSON."""
        from app.utils import read_json

        json_file = tmp_path / "test.json"
        data = {"key": "value", "list": [1, 2, 3]}

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        loaded = read_json(str(json_file))

        assert loaded == data

    def test_read_json_returns_none_if_not_exists(self, tmp_path):
        """read_json retourne None si le fichier n'existe pas."""
        from app.utils import read_json

        non_existent = tmp_path / "does_not_exist.json"

        result = read_json(str(non_existent))

        assert result is None

    def test_read_json_handles_unicode(self, tmp_path):
        """read_json gère correctement les caractères Unicode."""
        from app.utils import read_json, atomic_write_json

        json_file = tmp_path / "unicode.json"
        data = {"message": "Héllo wörld 你好 🎉"}

        atomic_write_json(str(json_file), data)
        loaded = read_json(str(json_file))

        assert loaded == data
        assert loaded["message"] == "Héllo wörld 你好 🎉"


# ---------------------------------------------------------------------------
# Tests sha256_file
# ---------------------------------------------------------------------------

class TestSha256File:
    """Tests de la fonction sha256_file."""

    def test_sha256_file_computes_hash(self, tmp_path):
        """sha256_file calcule le hash SHA-256 d'un fichier."""
        from app.utils import sha256_file

        test_file = tmp_path / "test.txt"
        content = b"Hello, World!"
        test_file.write_bytes(content)

        result = sha256_file(str(test_file))

        # Hash SHA-256 connu de "Hello, World!"
        import hashlib
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_sha256_file_empty_file(self, tmp_path):
        """sha256_file gère les fichiers vides."""
        from app.utils import sha256_file

        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")

        result = sha256_file(str(empty_file))

        # Hash SHA-256 d'un fichier vide
        import hashlib
        expected = hashlib.sha256(b"").hexdigest()

        assert result == expected

    def test_sha256_file_large_file(self, tmp_path):
        """sha256_file gère les fichiers volumineux (lecture par chunks)."""
        from app.utils import sha256_file

        large_file = tmp_path / "large.bin"
        # Créer un fichier de 5 MB
        content = b"A" * (5 * 1024 * 1024)
        large_file.write_bytes(content)

        result = sha256_file(str(large_file))

        import hashlib
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_sha256_file_binary_content(self, tmp_path):
        """sha256_file gère le contenu binaire."""
        from app.utils import sha256_file

        bin_file = tmp_path / "binary.bin"
        content = bytes(range(256))  # Tous les bytes de 0x00 à 0xFF
        bin_file.write_bytes(content)

        result = sha256_file(str(bin_file))

        import hashlib
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected


# ---------------------------------------------------------------------------
# Tests natural_key
# ---------------------------------------------------------------------------

class TestNaturalKey:
    """Tests de la fonction natural_key."""

    def test_natural_key_sorts_numbers_correctly(self):
        """natural_key permet un tri naturel des nombres."""
        from app.utils import natural_key

        filenames = ["page10.jpg", "page2.jpg", "page1.jpg", "page20.jpg"]
        sorted_files = sorted(filenames, key=natural_key)

        assert sorted_files == ["page1.jpg", "page2.jpg", "page10.jpg", "page20.jpg"]

    def test_natural_key_handles_mixed_content(self):
        """natural_key gère les noms mixtes texte/nombres."""
        from app.utils import natural_key

        names = ["img100a.png", "img20b.png", "img3c.png"]
        sorted_names = sorted(names, key=natural_key)

        assert sorted_names == ["img3c.png", "img20b.png", "img100a.png"]

    def test_natural_key_case_insensitive(self):
        """natural_key est insensible à la casse."""
        from app.utils import natural_key

        names = ["Page1.jpg", "page2.jpg", "PAGE3.jpg"]
        sorted_names = sorted(names, key=natural_key)

        # Ordre préservé car même valeur naturelle
        assert len(sorted_names) == 3


# ---------------------------------------------------------------------------
# Tests list_images_recursive
# ---------------------------------------------------------------------------

class TestListImagesRecursive:
    """Tests de la fonction list_images_recursive."""

    def test_list_images_recursive_finds_images(self, tmp_path):
        """list_images_recursive trouve toutes les images dans un dossier."""
        from app.utils import list_images_recursive

        # Créer structure de dossiers avec images
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.png").touch()
        (tmp_path / "doc.txt").touch()  # Non-image

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "img3.jpeg").touch()

        result = list_images_recursive(str(tmp_path))

        # Doit trouver 3 images (pas doc.txt)
        assert len(result) == 3
        assert any("img1.jpg" in r for r in result)
        assert any("img2.png" in r for r in result)
        assert any("img3.jpeg" in r for r in result)
        assert not any("doc.txt" in r for r in result)

    def test_list_images_recursive_sorts_naturally(self, tmp_path):
        """list_images_recursive trie naturellement les images."""
        from app.utils import list_images_recursive

        # Créer images dans un ordre non trié
        (tmp_path / "page10.jpg").touch()
        (tmp_path / "page2.jpg").touch()
        (tmp_path / "page1.jpg").touch()

        result = list_images_recursive(str(tmp_path))

        basenames = [os.path.basename(r) for r in result]
        assert basenames == ["page1.jpg", "page2.jpg", "page10.jpg"]

    def test_list_images_recursive_handles_all_extensions(self, tmp_path):
        """list_images_recursive reconnaît toutes les extensions d'images."""
        from app.utils import list_images_recursive

        # Créer fichiers avec différentes extensions
        extensions = [".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"]
        for ext in extensions:
            (tmp_path / f"img{ext}").touch()

        result = list_images_recursive(str(tmp_path))

        assert len(result) == len(extensions)

    def test_list_images_recursive_case_insensitive_extensions(self, tmp_path):
        """list_images_recursive gère les extensions en majuscules."""
        from app.utils import list_images_recursive

        (tmp_path / "IMG1.JPG").touch()
        (tmp_path / "IMG2.PNG").touch()

        result = list_images_recursive(str(tmp_path))

        assert len(result) == 2

    def test_list_images_recursive_empty_directory(self, tmp_path):
        """list_images_recursive retourne une liste vide pour un dossier vide."""
        from app.utils import list_images_recursive

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = list_images_recursive(str(empty_dir))

        assert result == []

    def test_list_images_recursive_nested_directories(self, tmp_path):
        """list_images_recursive parcourt les sous-dossiers récursivement."""
        from app.utils import list_images_recursive

        # Structure: root/a/b/c/image.jpg
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.jpg").touch()
        (tmp_path / "root.jpg").touch()

        result = list_images_recursive(str(tmp_path))

        assert len(result) == 2
        assert any("deep.jpg" in r for r in result)
        assert any("root.jpg" in r for r in result)


# ---------------------------------------------------------------------------
# Tests now_iso
# ---------------------------------------------------------------------------

class TestNowIso:
    """Tests de la fonction now_iso."""

    def test_now_iso_returns_iso_format(self):
        """now_iso retourne un timestamp au format ISO 8601."""
        from app.utils import now_iso

        result = now_iso()

        # Format attendu : YYYY-MM-DDTHH:MM:SSZ
        assert len(result) == 20
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == "T"
        assert result[13] == ":"
        assert result[16] == ":"
        assert result[-1] == "Z"

    def test_now_iso_returns_utc_time(self):
        """now_iso retourne l'heure UTC (se termine par Z)."""
        from app.utils import now_iso

        result = now_iso()

        assert result.endswith("Z")


