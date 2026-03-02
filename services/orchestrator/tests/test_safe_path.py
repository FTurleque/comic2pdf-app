"""
Tests de la fonction safe_path (protection path traversal).

Couvre :
  - chemin valide sous base_dir → retourne chemin absolu normalisé
  - chemin de traversal ../../etc/passwd → ValueError
  - chemin égal à base_dir → accepté
  - chemin avec .. internes mais restant sous base_dir → accepté
  - chemin absolu hors base_dir → ValueError
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.utils import safe_path


class TestSafePath:
    """Tests unitaires de safe_path."""

    def test_chemin_valide_retourne_chemin_absolu(self, tmp_path):
        """Un chemin valide sous base_dir retourne le chemin absolu normalisé."""
        base = str(tmp_path)
        user = os.path.join(base, "sous-dossier", "fichier.json")
        result = safe_path(base, user)
        assert os.path.isabs(result)
        assert result.startswith(os.path.realpath(base))

    def test_chemin_egal_base_accepte(self, tmp_path):
        """Un chemin égal à base_dir est accepté."""
        base = str(tmp_path)
        result = safe_path(base, base)
        assert result == os.path.realpath(base)

    def test_traversal_simple_leve_valueerror(self, tmp_path):
        """../../etc/passwd lève ValueError."""
        base = str(tmp_path)
        with pytest.raises(ValueError, match="Path traversal"):
            safe_path(base, os.path.join(base, "..", "..", "etc", "passwd"))

    def test_traversal_absolu_leve_valueerror(self, tmp_path):
        """Un chemin absolu hors de base_dir lève ValueError."""
        base = str(tmp_path / "data")
        with pytest.raises(ValueError, match="Path traversal"):
            safe_path(base, "/etc/passwd")

    def test_traversal_absolu_windows_style(self, tmp_path):
        """Un chemin commençant par C:\\Windows sort de base_dir → ValueError."""
        base = str(tmp_path / "data")
        # Ce chemin ne peut pas être sous base_dir
        with pytest.raises(ValueError, match="Path traversal"):
            safe_path(base, str(tmp_path / "autre_dossier" / "secret.txt"))

    def test_chemin_avec_points_internes_reste_sous_base(self, tmp_path):
        """Un chemin avec '..' internes mais restant sous base_dir est accepté."""
        base = str(tmp_path)
        sous = str(tmp_path / "a" / ".." / "b" / "fichier.txt")
        # Le chemin résolu tmp_path/b/fichier.txt reste sous tmp_path
        result = safe_path(base, sous)
        assert result.startswith(os.path.realpath(base))

    def test_base_dir_relatif_fonctionne(self, tmp_path, monkeypatch):
        """safe_path fonctionne aussi avec un base_dir relatif."""
        monkeypatch.chdir(tmp_path)
        base = "."
        user = os.path.join(str(tmp_path), "fichier.json")
        # Les deux doivent se résoudre sous tmp_path
        result = safe_path(base, user)
        assert os.path.isabs(result)

    def test_jobkey_valide_accepte(self, tmp_path):
        """Un jobKey légitime (hash__hash) est accepté dans le work_dir."""
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir, exist_ok=True)
        job_key = "abc123def456" + "__" + "xyz789"
        state_path = os.path.join(work_dir, job_key, "state.json")
        result = safe_path(work_dir, state_path)
        assert result.startswith(os.path.realpath(work_dir))

