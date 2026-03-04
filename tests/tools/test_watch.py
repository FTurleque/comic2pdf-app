"""
Tests unitaires — tools/watch_local.py

Vérifie le parsing, la détection de fichiers, la gestion des doublons
et la boucle principale (subprocess entièrement mocké).
"""
import json
import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.watch_local import (
    build_parser,
    scan_for_new_files,
    load_processed,
    save_processed,
    handle_duplicate,
    process_file,
    watch_loop,
    main,
)
from tools.deps import MissingDepError


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    """Tests du parser argparse du watcher."""

    def test_valeurs_par_defaut(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.in_dir == "./data/in"
        assert args.out_dir == "./data/out"
        assert args.lang == "fra+eng"
        assert args.poll_interval == 2.0
        assert args.no_ocr is False
        assert args.keep_temp is False

    def test_options_personnalisees(self):
        parser = build_parser()
        args = parser.parse_args([
            "--in", "/tmp/in",
            "--out", "/tmp/out",
            "--lang", "eng",
            "--poll-interval", "5",
            "--no-ocr",
        ])
        assert args.in_dir == "/tmp/in"
        assert args.out_dir == "/tmp/out"
        assert args.lang == "eng"
        assert args.poll_interval == 5.0
        assert args.no_ocr is True

    def test_check_deps_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--check-deps"])
        assert args.check_deps is True


# ---------------------------------------------------------------------------
# scan_for_new_files
# ---------------------------------------------------------------------------

class TestScanForNewFiles:
    """Tests du scan des fichiers entrants."""

    def test_retourne_cbz_et_cbr(self, tmp_path):
        (tmp_path / "a.cbz").write_bytes(b"x")
        (tmp_path / "b.cbr").write_bytes(b"x")
        (tmp_path / "c.txt").write_bytes(b"x")
        result = scan_for_new_files(str(tmp_path))
        noms = {os.path.basename(p) for p in result}
        assert "a.cbz" in noms
        assert "b.cbr" in noms
        assert "c.txt" not in noms

    def test_ignore_fichiers_part(self, tmp_path):
        """Les fichiers .part (en cours de copie) sont ignorés."""
        (tmp_path / "a.cbz.part").write_bytes(b"x")
        (tmp_path / "b.cbz").write_bytes(b"x")
        result = scan_for_new_files(str(tmp_path))
        noms = {os.path.basename(p) for p in result}
        assert "a.cbz.part" not in noms
        assert "b.cbz" in noms

    def test_dossier_absent_retourne_liste_vide(self, tmp_path):
        result = scan_for_new_files(str(tmp_path / "absent"))
        assert result == []

    def test_dossier_vide(self, tmp_path):
        result = scan_for_new_files(str(tmp_path))
        assert result == []


# ---------------------------------------------------------------------------
# load_processed / save_processed
# ---------------------------------------------------------------------------

class TestProcessedDb:
    """Tests de la persistance des fichiers traités."""

    def test_load_retourne_dict_vide_si_absent(self, tmp_path):
        result = load_processed(str(tmp_path / "absent.json"))
        assert result == {}

    def test_save_et_reload(self, tmp_path):
        db = str(tmp_path / "processed.json")
        state = {"key1": {"fileName": "a.cbz", "processedAt": "2026-03-04T12:00:00Z"}}
        save_processed(db, state)
        loaded = load_processed(db)
        assert loaded == state

    def test_save_atomique_pas_de_tmp_residuel(self, tmp_path):
        db = str(tmp_path / "processed.json")
        save_processed(db, {"x": 1})
        assert not os.path.isfile(db + ".tmp")


# ---------------------------------------------------------------------------
# handle_duplicate
# ---------------------------------------------------------------------------

class TestHandleDuplicate:
    """Tests de la gestion des doublons."""

    def test_deplace_fichier_vers_hold(self, tmp_path):
        cbz = str(tmp_path / "comic.cbz")
        with open(cbz, "wb") as f:
            f.write(b"\x50\x4B\x03\x04" + b"\x00" * 8)
        hold_dir = str(tmp_path / "hold")
        existing = {"outputPdf": "/out/existing.pdf"}

        handle_duplicate(cbz, "job_key_123", existing, hold_dir)

        # Le fichier original ne doit plus être à sa place
        assert not os.path.isfile(cbz)
        # Il doit être dans hold/job_key_123/
        dest_dir = os.path.join(hold_dir, "job_key_123")
        assert os.path.isdir(dest_dir)
        moved_files = os.listdir(dest_dir)
        assert len(moved_files) == 1
        assert "comic.cbz" in moved_files[0]

    def test_affiche_message_doublon(self, tmp_path, capsys):
        cbz = str(tmp_path / "comic.cbz")
        with open(cbz, "wb") as f:
            f.write(b"\x50\x4B\x03\x04" + b"\x00" * 8)
        hold_dir = str(tmp_path / "hold")
        existing = {"outputPdf": "/out/existing.pdf"}

        handle_duplicate(cbz, "jk", existing, hold_dir)
        out = capsys.readouterr().out
        assert "DOUBLON" in out


# ---------------------------------------------------------------------------
# process_file
# ---------------------------------------------------------------------------

class TestProcessFile:
    """Tests de process_file avec subprocess mocké."""

    def _make_valid_cbz(self, tmp_path) -> str:
        import zipfile
        p = str(tmp_path / "test.cbz")
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("001.jpg", b"\xff\xd8\xff" + b"\x00" * 100)
        return p

    def test_ignore_si_signature_invalide(self, tmp_path, capsys):
        """process_file ignore silencieusement les fichiers à signature invalide."""
        p = str(tmp_path / "bad.cbz")
        with open(p, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07")
        processed = {}
        db_path = str(tmp_path / "processed.json")
        process_file(p, str(tmp_path / "out"), "fra+eng", True, False,
                     str(tmp_path / "hold"), processed, db_path)
        out = capsys.readouterr().out
        assert "IGNORÉ" in out
        assert processed == {}

    def test_detecte_doublon(self, tmp_path, mocker, capsys):
        """process_file détecte un doublon et déplace le fichier."""
        cbz = self._make_valid_cbz(tmp_path)
        hold_dir = str(tmp_path / "hold")
        # Simuler que ce jobKey existe déjà
        mocker.patch(
            "tools.watch_local.sha256_file",
            return_value="aabbcc",
        )
        mocker.patch(
            "tools.watch_local.make_job_key",
            return_value=("phash", "existing_job_key"),
        )
        processed = {"existing_job_key": {"fileName": "old.cbz", "outputPdf": "/out/old.pdf"}}
        db_path = str(tmp_path / "processed.json")

        process_file(cbz, str(tmp_path / "out"), "fra+eng", True, False,
                     hold_dir, processed, db_path)

        out = capsys.readouterr().out
        assert "DOUBLON" in out

    def test_traite_fichier_et_met_a_jour_processed(self, tmp_path, mocker):
        """process_file appelle run_pipeline et met à jour la base."""
        cbz = self._make_valid_cbz(tmp_path)
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir, exist_ok=True)
        hold_dir = str(tmp_path / "hold")

        mocker.patch("tools.watch_local.sha256_file", return_value="filehash123")
        mocker.patch(
            "tools.watch_local.make_job_key",
            return_value=("phash", "new_job_key"),
        )
        expected_pdf = os.path.join(out_dir, "test__job-new_job_key.pdf")
        mocker.patch("tools.watch_local.run_pipeline", return_value=expected_pdf)

        processed = {}
        db_path = str(tmp_path / "processed.json")

        process_file(cbz, out_dir, "fra+eng", True, False,
                     hold_dir, processed, db_path)

        assert "new_job_key" in processed
        assert processed["new_job_key"]["outputPdf"] == expected_pdf
        # La base doit être persistée
        assert os.path.isfile(db_path)


# ---------------------------------------------------------------------------
# watch_loop
# ---------------------------------------------------------------------------

class TestWatchLoop:
    """Tests de la boucle de surveillance."""

    def test_boucle_s_arrete_apres_n_iterations(self, tmp_path, mocker):
        """watch_loop s'arrête après stop_after itérations."""
        in_dir = str(tmp_path / "in")
        out_dir = str(tmp_path / "out")
        hold_dir = str(tmp_path / "hold")
        os.makedirs(in_dir)
        os.makedirs(out_dir)
        os.makedirs(hold_dir)

        mocker.patch("tools.watch_local.time.sleep")  # Pas de vraie attente
        mocker.patch("tools.watch_local.scan_for_new_files", return_value=[])

        # Ne doit pas lever et doit s'arrêter
        watch_loop(
            in_dir=in_dir,
            out_dir=out_dir,
            lang="fra+eng",
            no_ocr=True,
            keep_temp=False,
            poll_interval=0.01,
            hold_dir=hold_dir,
            stop_after=2,
        )

    def test_traite_fichier_detecte(self, tmp_path, mocker):
        """watch_loop appelle process_file pour chaque fichier détecté."""
        in_dir = str(tmp_path / "in")
        out_dir = str(tmp_path / "out")
        hold_dir = str(tmp_path / "hold")
        for d in [in_dir, out_dir, hold_dir]:
            os.makedirs(d)

        fake_file = str(tmp_path / "in" / "test.cbz")
        mocker.patch("tools.watch_local.time.sleep")
        mocker.patch("tools.watch_local.scan_for_new_files", return_value=[fake_file])
        mock_process = mocker.patch("tools.watch_local.process_file")

        watch_loop(
            in_dir=in_dir,
            out_dir=out_dir,
            lang="fra+eng",
            no_ocr=True,
            keep_temp=False,
            poll_interval=0.01,
            hold_dir=hold_dir,
            stop_after=1,
        )

        mock_process.assert_called_once()
        call_kwargs = mock_process.call_args
        assert call_kwargs[1]["input_path"] == fake_file or \
               fake_file in call_kwargs[0]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    """Tests du point d'entrée main() du watcher."""

    def test_check_deps_retourne_0(self, mocker, capsys):
        mocker.patch("tools.watch_local.check_deps_report", return_value="OK")
        result = main(["--check-deps"])
        assert result == 0

    def test_deps_manquantes_retourne_1(self, mocker):
        mocker.patch(
            "tools.watch_local.check_all_deps",
            side_effect=MissingDepError("7z", "7z manquant"),
        )
        result = main([])
        assert result == 1

