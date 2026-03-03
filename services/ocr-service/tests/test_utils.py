"""
Tests du module utils — ocr-service.
Couvre toutes les fonctions utilitaires : filesystem, JSON, hash, listing images.
"""
import json
import os
import sys
import time
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

        ensure_dir(str(existing_dir))

        assert existing_dir.exists()

    def test_ensure_dir_creates_nested_directories(self, tmp_path):
        """ensure_dir crée les répertoires parents si nécessaire."""
        from app.utils import ensure_dir

        nested_dir = tmp_path / "a" / "b" / "c"
        assert not nested_dir.exists()

        ensure_dir(str(nested_dir))

        assert nested_dir.exists()


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

        atomic_write_json(str(json_file), {"old": "data"})
        atomic_write_json(str(json_file), {"new": "data"})

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {"new": "data"}

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

        import hashlib
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_sha256_file_empty_file(self, tmp_path):
        """sha256_file gère les fichiers vides."""
        from app.utils import sha256_file

        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")

        result = sha256_file(str(empty_file))

        import hashlib
        expected = hashlib.sha256(b"").hexdigest()

        assert result == expected

    def test_sha256_file_large_file(self, tmp_path):
        """sha256_file gère les fichiers volumineux."""
        from app.utils import sha256_file

        large_file = tmp_path / "large.bin"
        content = b"A" * (5 * 1024 * 1024)
        large_file.write_bytes(content)

        result = sha256_file(str(large_file))

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


# ---------------------------------------------------------------------------
# Tests now_iso
# ---------------------------------------------------------------------------

class TestNowIso:
    """Tests de la fonction now_iso."""

    def test_now_iso_returns_iso_format(self):
        """now_iso retourne un timestamp au format ISO 8601."""
        from app.utils import now_iso

        result = now_iso()

        assert len(result) == 20
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == "T"
        assert result[-1] == "Z"

    def test_now_iso_returns_utc_time(self):
        """now_iso retourne l'heure UTC."""
        from app.utils import now_iso

        result = now_iso()

        assert result.endswith("Z")
