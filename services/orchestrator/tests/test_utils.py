"""
Tests du module utils — orchestrator.
Couvre sha256_file, natural_key, list_images_recursive et now_iso.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Tests sha256_file
# ---------------------------------------------------------------------------

class TestSha256File:
    """Tests de la fonction sha256_file."""

    def test_sha256_file_computes_hash(self, tmp_path):
        from app.utils import sha256_file

        test_file = tmp_path / "test.txt"
        content = b"Hello, Orchestrator!"
        test_file.write_bytes(content)

        result = sha256_file(str(test_file))

        import hashlib
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_sha256_file_empty(self, tmp_path):
        from app.utils import sha256_file

        empty = tmp_path / "empty.bin"
        empty.write_bytes(b"")

        result = sha256_file(str(empty))

        import hashlib
        expected = hashlib.sha256(b"").hexdigest()

        assert result == expected


# ---------------------------------------------------------------------------
# Tests natural_key
# ---------------------------------------------------------------------------

class TestNaturalKey:
    """Tests de natural_key."""

    def test_sort_numbers(self):
        from app.utils import natural_key

        files = ["10.jpg", "2.jpg", "1.jpg"]
        sorted_files = sorted(files, key=natural_key)
        assert sorted_files == ["1.jpg", "2.jpg", "10.jpg"]

    def test_mixed(self):
        from app.utils import natural_key

        names = ["img100a.png", "img20b.png", "img3c.png"]
        assert sorted(names, key=natural_key) == ["img3c.png", "img20b.png", "img100a.png"]


# ---------------------------------------------------------------------------
# Tests list_images_recursive
# ---------------------------------------------------------------------------

class TestListImagesRecursive:
    def test_finds_and_sorts(self, tmp_path):
        from app.utils import list_images_recursive

        (tmp_path / "p10.jpg").write_bytes(b"x")
        (tmp_path / "p2.jpg").write_bytes(b"x")
        (tmp_path / "p1.jpg").write_bytes(b"x")

        res = list_images_recursive(str(tmp_path))
        basenames = [os.path.basename(r) for r in res]
        assert basenames == ["p1.jpg", "p2.jpg", "p10.jpg"]

    def test_handles_extensions_and_nested(self, tmp_path):
        from app.utils import list_images_recursive

        (tmp_path / "a" / "b").mkdir(parents=True)
        (tmp_path / "a" / "b" / "deep.PNG").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")

        res = list_images_recursive(str(tmp_path))
        assert any("deep.PNG" in r for r in res) or any("deep.png" in r for r in res)
        assert any("cover.jpg" in r for r in res)


# ---------------------------------------------------------------------------
# Tests now_iso
# ---------------------------------------------------------------------------

class TestNowIso:
    def test_format_and_suffix(self):
        from app.utils import now_iso

        s = now_iso()
        assert len(s) == 20
        assert s[4] == '-'
        assert s[7] == '-'
        assert s[10] == 'T'
        assert s.endswith('Z')


