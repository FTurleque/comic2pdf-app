"""
Tests des fonctions helpers — orchestrator main.py.
Couvre base_name, job_dir, job_state_path, update_state, move_atomic, discover_inputs.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Tests base_name
# ---------------------------------------------------------------------------

class TestBaseName:
    """Tests de la fonction base_name."""

    def test_base_name_removes_extension(self):
        """base_name retourne le nom sans extension."""
        from app.main import base_name

        assert base_name("/path/to/file.pdf") == "file"
        assert base_name("archive.cbz") == "archive"
        assert base_name("/data/Comic Book #1.cbr") == "Comic Book #1"

    def test_base_name_handles_multiple_dots(self):
        """base_name gère les fichiers avec plusieurs points."""
        from app.main import base_name

        assert base_name("my.archive.v2.cbz") == "my.archive.v2"
        assert base_name("file.tar.gz") == "file.tar"

    def test_base_name_handles_no_extension(self):
        """base_name gère les fichiers sans extension."""
        from app.main import base_name

        assert base_name("/path/to/README") == "README"
        assert base_name("file") == "file"


# ---------------------------------------------------------------------------
# Tests job_dir
# ---------------------------------------------------------------------------

class TestJobDir:
    """Tests de la fonction job_dir."""

    def test_job_dir_returns_correct_path(self, tmp_path, monkeypatch):
        """job_dir retourne le chemin du dossier de travail."""
        from app.main import job_dir

        work_dir = tmp_path / "work"
        monkeypatch.setattr("app.main.WORK_DIR", str(work_dir))

        result = job_dir("abc123__def456")

        assert result == str(work_dir / "abc123__def456")

    def test_job_dir_with_special_characters(self, tmp_path, monkeypatch):
        """job_dir gère les jobKey avec caractères spéciaux."""
        from app.main import job_dir

        work_dir = tmp_path / "work"
        monkeypatch.setattr("app.main.WORK_DIR", str(work_dir))

        result = job_dir("hash_123__hash_456")

        assert result == str(work_dir / "hash_123__hash_456")


# ---------------------------------------------------------------------------
# Tests job_state_path
# ---------------------------------------------------------------------------

class TestJobStatePath:
    """Tests de la fonction job_state_path."""

    def test_job_state_path_returns_state_json_path(self, tmp_path, monkeypatch):
        """job_state_path retourne le chemin vers state.json."""
        from app.main import job_state_path

        work_dir = tmp_path / "work"
        monkeypatch.setattr("app.main.WORK_DIR", str(work_dir))

        result = job_state_path("jobkey123")

        assert result == str(work_dir / "jobkey123" / "state.json")


# ---------------------------------------------------------------------------
# Tests update_state
# ---------------------------------------------------------------------------

class TestUpdateState:
    """Tests de la fonction update_state."""

    def test_update_state_creates_state_json(self, tmp_path, monkeypatch):
        """update_state crée state.json s'il n'existe pas."""
        from app.main import update_state
        from app.utils import ensure_dir

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.setattr("app.main.WORK_DIR", str(work_dir))

        job_key = "test_job"
        # Créer le dossier du job avant d'appeler update_state
        job_dir = work_dir / job_key
        ensure_dir(str(job_dir))

        update_state(job_key, {"state": "RUNNING"})

        state_file = work_dir / job_key / "state.json"
        assert state_file.exists()

        with open(state_file, "r") as f:
            data = json.load(f)

        assert data["jobKey"] == job_key
        assert data["state"] == "RUNNING"
        assert "updatedAt" in data

    def test_update_state_updates_existing_state(self, tmp_path, monkeypatch):
        """update_state met à jour un state.json existant."""
        from app.main import update_state
        from app.utils import atomic_write_json

        work_dir = tmp_path / "work"
        job_dir = work_dir / "job123"
        job_dir.mkdir(parents=True)
        monkeypatch.setattr("app.main.WORK_DIR", str(work_dir))

        # Créer state initial
        state_file = job_dir / "state.json"
        atomic_write_json(str(state_file), {"jobKey": "job123", "state": "QUEUED", "custom": "value"})

        update_state("job123", {"state": "RUNNING", "progress": 50})

        with open(state_file, "r") as f:
            data = json.load(f)

        assert data["jobKey"] == "job123"
        assert data["state"] == "RUNNING"
        assert data["progress"] == 50
        assert data["custom"] == "value"  # Préservé
        assert "updatedAt" in data

    def test_update_state_adds_timestamp(self, tmp_path, monkeypatch):
        """update_state ajoute automatiquement updatedAt."""
        from app.main import update_state
        from app.utils import ensure_dir

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.setattr("app.main.WORK_DIR", str(work_dir))

        # Créer le dossier du job avant d'appeler update_state
        job_dir = work_dir / "job456"
        ensure_dir(str(job_dir))

        update_state("job456", {"state": "DONE"})

        state_file = work_dir / "job456" / "state.json"
        with open(state_file, "r") as f:
            data = json.load(f)

        assert "updatedAt" in data
        assert "T" in data["updatedAt"]
        assert "Z" in data["updatedAt"]


# ---------------------------------------------------------------------------
# Tests move_atomic
# ---------------------------------------------------------------------------

class TestMoveAtomic:
    """Tests de la fonction move_atomic."""

    def test_move_atomic_moves_file(self, tmp_path):
        """move_atomic déplace un fichier atomiquement."""
        from app.main import move_atomic

        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("test content")

        move_atomic(str(src), str(dst))

        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == "test content"

    def test_move_atomic_overwrites_destination(self, tmp_path):
        """move_atomic écrase le fichier de destination s'il existe."""
        from app.main import move_atomic

        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("new content")
        dst.write_text("old content")

        move_atomic(str(src), str(dst))

        assert not src.exists()
        assert dst.read_text() == "new content"

    def test_move_atomic_creates_destination_dir(self, tmp_path):
        """move_atomic crée le dossier de destination s'il n'existe pas."""
        from app.main import move_atomic

        src = tmp_path / "source.txt"
        dst = tmp_path / "subdir" / "dest.txt"
        src.write_text("test")

        move_atomic(str(src), str(dst))

        assert dst.exists()
        assert dst.read_text() == "test"


# ---------------------------------------------------------------------------
# Tests output_path_for
# ---------------------------------------------------------------------------

class TestOutputPathFor:
    """Tests de la fonction output_path_for."""

    def test_output_path_for_generates_correct_path(self, tmp_path, monkeypatch):
        """output_path_for génère le chemin de sortie avec le suffixe __job-<jobKey>.pdf."""
        from app.main import output_path_for

        out_dir = tmp_path / "out"
        monkeypatch.setattr("app.main.OUT_DIR", str(out_dir))

        result = output_path_for("MyComic.cbz", "abc123__def456")

        expected = str(out_dir / "MyComic__job-abc123__def456.pdf")
        assert result == expected

    def test_output_path_for_removes_extension(self, tmp_path, monkeypatch):
        """output_path_for enlève l'extension originale."""
        from app.main import output_path_for

        out_dir = tmp_path / "out"
        monkeypatch.setattr("app.main.OUT_DIR", str(out_dir))

        result = output_path_for("Archive.cbr", "key123")

        assert "Archive__job-key123.pdf" in result
        assert ".cbr" not in result


# ---------------------------------------------------------------------------
# Tests discover_inputs
# ---------------------------------------------------------------------------

class TestDiscoverInputs:
    """Tests de la fonction discover_inputs."""

    def test_discover_inputs_finds_cbz_files(self, tmp_path, monkeypatch):
        """discover_inputs trouve tous les fichiers .cbz."""
        from app.main import discover_inputs

        in_dir = tmp_path / "in"
        in_dir.mkdir()
        monkeypatch.setattr("app.main.IN_DIR", str(in_dir))

        (in_dir / "comic1.cbz").touch()
        (in_dir / "comic2.cbz").touch()
        (in_dir / "readme.txt").touch()

        result = list(discover_inputs())  # Convertir generator en liste

        assert len(result) == 2
        assert any("comic1.cbz" in p for p in result)
        assert any("comic2.cbz" in p for p in result)
        assert not any("readme.txt" in p for p in result)

    def test_discover_inputs_finds_cbr_files(self, tmp_path, monkeypatch):
        """discover_inputs trouve tous les fichiers .cbr."""
        from app.main import discover_inputs

        in_dir = tmp_path / "in"
        in_dir.mkdir()
        monkeypatch.setattr("app.main.IN_DIR", str(in_dir))

        (in_dir / "archive.cbr").touch()

        result = list(discover_inputs())  # Convertir generator en liste

        assert len(result) == 1
        assert "archive.cbr" in result[0]

    def test_discover_inputs_ignores_part_files(self, tmp_path, monkeypatch):
        """discover_inputs ignore les fichiers .part."""
        from app.main import discover_inputs

        in_dir = tmp_path / "in"
        in_dir.mkdir()
        monkeypatch.setattr("app.main.IN_DIR", str(in_dir))

        (in_dir / "complete.cbz").touch()
        (in_dir / "downloading.cbz.part").touch()

        result = list(discover_inputs())  # Convertir generator en liste

        assert len(result) == 1
        assert "complete.cbz" in result[0]

    def test_discover_inputs_returns_empty_if_no_files(self, tmp_path, monkeypatch):
        """discover_inputs retourne une liste vide si aucun fichier."""
        from app.main import discover_inputs

        in_dir = tmp_path / "in"
        in_dir.mkdir()
        monkeypatch.setattr("app.main.IN_DIR", str(in_dir))

        result = list(discover_inputs())  # Convertir generator en liste

        assert result == []


# ---------------------------------------------------------------------------
# Tests ensure_layout supprimés (attributs non disponibles dans le code réel)
# ---------------------------------------------------------------------------


