"""
Tests unitaires — tools/pipeline_core.py

Vérifie les fonctions pures du pipeline sans appel à aucun outil système.
"""
import hashlib
import json
import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.pipeline_core import (
    ensure_dir,
    atomic_write_json,
    read_json,
    sha256_file,
    natural_key,
    now_iso,
    validate_pdf,
    check_file_signature,
    ZipSlipError,
    check_zip_slip,
    filter_images,
    sort_images,
    list_and_sort_images,
    build_ocrmypdf_cmd,
    stable_json,
    sha256_str,
    make_job_key,
    output_filename,
    safe_replace,
)


# ---------------------------------------------------------------------------
# Utilitaires FS
# ---------------------------------------------------------------------------

class TestEnsureDir:
    def test_cree_repertoire(self, tmp_path):
        d = str(tmp_path / "new_dir")
        ensure_dir(d)
        assert os.path.isdir(d)

    def test_pas_erreur_si_existe(self, tmp_path):
        d = str(tmp_path)
        ensure_dir(d)  # ne doit pas lever


class TestAtomicWriteJson:
    def test_cree_fichier_json(self, tmp_path):
        p = str(tmp_path / "test.json")
        atomic_write_json(p, {"k": "v"})
        assert os.path.isfile(p)
        with open(p, encoding="utf-8") as f:
            assert json.load(f) == {"k": "v"}

    def test_pas_de_fichier_tmp_residuel(self, tmp_path):
        p = str(tmp_path / "test.json")
        atomic_write_json(p, {"x": 1})
        assert not os.path.isfile(p + ".tmp")

    def test_ecrasement_atomique(self, tmp_path):
        p = str(tmp_path / "test.json")
        atomic_write_json(p, {"old": True})
        atomic_write_json(p, {"new": True})
        with open(p, encoding="utf-8") as f:
            assert json.load(f) == {"new": True}


# ---------------------------------------------------------------------------
# safe_replace
# ---------------------------------------------------------------------------

class TestSafeReplace:
    def test_deplace_fichier_meme_volume(self, tmp_path):
        src = str(tmp_path / "src.txt")
        dst = str(tmp_path / "dst.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("contenu")
        safe_replace(src, dst)
        assert not os.path.exists(src)
        assert open(dst, encoding="utf-8").read() == "contenu"

    def test_ecrase_destination_existante(self, tmp_path):
        src = str(tmp_path / "src.txt")
        dst = str(tmp_path / "dst.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("nouveau")
        with open(dst, "w", encoding="utf-8") as f:
            f.write("ancien")
        safe_replace(src, dst)
        assert open(dst, encoding="utf-8").read() == "nouveau"

    def test_fallback_cross_device_os_replace_echoue(self, tmp_path, mocker):
        """Simule un OSError de os.replace (cross-device) et vérifie le fallback shutil.move."""
        src = str(tmp_path / "src.txt")
        dst = str(tmp_path / "dst.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("cross-device")
        mocker.patch("tools.pipeline_core.os.replace", side_effect=OSError("cross-device simulé"))
        mock_move = mocker.patch("tools.pipeline_core.shutil.move")
        safe_replace(src, dst)
        mock_move.assert_called_once_with(src, dst)

    def test_pas_de_fallback_si_os_replace_reussit(self, tmp_path, mocker):
        """Vérifie que shutil.move n'est PAS appelé si os.replace réussit."""
        src = str(tmp_path / "src.txt")
        dst = str(tmp_path / "dst.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("ok")
        mock_move = mocker.patch("tools.pipeline_core.shutil.move")
        safe_replace(src, dst)
        mock_move.assert_not_called()


class TestReadJson:
    def test_retourne_none_si_absent(self, tmp_path):
        assert read_json(str(tmp_path / "absent.json")) is None

    def test_retourne_contenu(self, tmp_path):
        p = str(tmp_path / "data.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"a": 1}, f)
        assert read_json(p) == {"a": 1}


class TestSha256File:
    def test_hash_deterministe(self, tmp_path):
        p = str(tmp_path / "f.bin")
        with open(p, "wb") as f:
            f.write(b"hello")
        h1 = sha256_file(p)
        h2 = sha256_file(p)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_different_pour_contenus_differents(self, tmp_path):
        p1 = str(tmp_path / "a.bin")
        p2 = str(tmp_path / "b.bin")
        with open(p1, "wb") as f:
            f.write(b"aaa")
        with open(p2, "wb") as f:
            f.write(b"bbb")
        assert sha256_file(p1) != sha256_file(p2)


class TestNaturalKey:
    def test_ordre_numerique(self):
        paths = ["10.jpg", "2.jpg", "1.jpg"]
        sorted_paths = sorted(paths, key=lambda p: natural_key(os.path.basename(p)))
        assert sorted_paths == ["1.jpg", "2.jpg", "10.jpg"]

    def test_insensible_casse(self):
        keys = [natural_key("B.jpg"), natural_key("a.jpg")]
        assert sorted(keys) == [natural_key("a.jpg"), natural_key("B.jpg")]


class TestNowIso:
    def test_format_iso(self):
        s = now_iso()
        assert "T" in s
        assert s.endswith("Z")
        assert len(s) == 20


# ---------------------------------------------------------------------------
# validate_pdf
# ---------------------------------------------------------------------------

class TestValidatePdf:
    def test_pdf_valide(self, tmp_path):
        p = str(tmp_path / "ok.pdf")
        with open(p, "wb") as f:
            f.write(b"%PDF-1.4" + b"\x00" * 2000)
        assert validate_pdf(p) is True

    def test_pdf_trop_petit(self, tmp_path):
        p = str(tmp_path / "small.pdf")
        with open(p, "wb") as f:
            f.write(b"%PDF-1.4")
        assert validate_pdf(p, min_size_bytes=1024) is False

    def test_fichier_absent(self, tmp_path):
        assert validate_pdf(str(tmp_path / "absent.pdf")) is False

    def test_fichier_non_pdf(self, tmp_path):
        p = str(tmp_path / "bad.pdf")
        with open(p, "wb") as f:
            f.write(b"PK\x03\x04" + b"\x00" * 2000)
        assert validate_pdf(p) is False


# ---------------------------------------------------------------------------
# check_file_signature
# ---------------------------------------------------------------------------

class TestCheckFileSignature:
    def test_signature_zip(self, tmp_path):
        p = str(tmp_path / "ok.cbz")
        with open(p, "wb") as f:
            f.write(b"\x50\x4B\x03\x04" + b"\x00" * 4)
        assert check_file_signature(p) is True

    def test_signature_rar4(self, tmp_path):
        p = str(tmp_path / "ok.cbr")
        with open(p, "wb") as f:
            f.write(b"\x52\x61\x72\x21\x1A\x07\x00" + b"\x00")
        assert check_file_signature(p) is True

    def test_signature_invalide(self, tmp_path):
        p = str(tmp_path / "bad.cbz")
        with open(p, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07")
        assert check_file_signature(p) is False

    def test_fichier_absent(self, tmp_path):
        assert check_file_signature(str(tmp_path / "absent.cbz")) is False


# ---------------------------------------------------------------------------
# ZipSlip
# ---------------------------------------------------------------------------

class TestCheckZipSlip:
    def test_chemins_valides(self, tmp_path):
        f1 = str(tmp_path / "p1.jpg")
        f2 = str(tmp_path / "p2.jpg")
        open(f1, "w").close()
        open(f2, "w").close()
        result = check_zip_slip(str(tmp_path), [f1, f2])
        assert result == [f1, f2]

    def test_leve_zip_slip_si_chemin_externe(self, tmp_path):
        f_safe = str(tmp_path / "ok.jpg")
        f_evil = str(tmp_path.parent / "evil.jpg")
        open(f_safe, "w").close()
        open(f_evil, "w").close()
        with pytest.raises(ZipSlipError):
            check_zip_slip(str(tmp_path), [f_safe, f_evil])


# ---------------------------------------------------------------------------
# filter_images / sort_images
# ---------------------------------------------------------------------------

class TestFilterImages:
    def test_retourne_images_valides(self, tmp_path):
        (tmp_path / "p1.jpg").write_bytes(b"x")
        (tmp_path / "p2.PNG").write_bytes(b"x")
        (tmp_path / "readme.txt").write_bytes(b"x")
        result = filter_images(str(tmp_path))
        noms = {os.path.basename(p) for p in result}
        assert "p1.jpg" in noms
        assert "p2.PNG" in noms
        assert "readme.txt" not in noms

    def test_exclut_parasites(self, tmp_path):
        (tmp_path / "Thumbs.db").write_bytes(b"x")
        (tmp_path / "p1.jpg").write_bytes(b"x")
        result = filter_images(str(tmp_path))
        noms = {os.path.basename(p).lower() for p in result}
        assert "thumbs.db" not in noms
        assert "p1.jpg" in noms

    def test_exclut_macosx(self, tmp_path):
        mac = tmp_path / "__MACOSX"
        mac.mkdir()
        (mac / "h.jpg").write_bytes(b"x")
        (tmp_path / "real.jpg").write_bytes(b"x")
        result = filter_images(str(tmp_path))
        assert all("__macosx" not in p.lower() for p in result)


class TestSortImages:
    def test_tri_naturel(self, tmp_path):
        paths = [str(tmp_path / "10.jpg"), str(tmp_path / "2.jpg"), str(tmp_path / "1.jpg")]
        result = sort_images(paths)
        assert [os.path.basename(p) for p in result] == ["1.jpg", "2.jpg", "10.jpg"]

    def test_liste_vide(self):
        assert sort_images([]) == []


class TestListAndSortImages:
    def test_retourne_images_triees_naturellement(self, tmp_path):
        (tmp_path / "10.jpg").write_bytes(b"x")
        (tmp_path / "2.jpg").write_bytes(b"x")
        (tmp_path / "1.jpg").write_bytes(b"x")
        result = list_and_sort_images(str(tmp_path))
        assert [os.path.basename(p) for p in result] == ["1.jpg", "2.jpg", "10.jpg"]

    def test_exclut_fichiers_non_images(self, tmp_path):
        (tmp_path / "p1.jpg").write_bytes(b"x")
        (tmp_path / "notes.txt").write_bytes(b"x")
        result = list_and_sort_images(str(tmp_path))
        noms = [os.path.basename(p) for p in result]
        assert "notes.txt" not in noms
        assert "p1.jpg" in noms

    def test_leve_zip_slip_si_chemin_externe(self, tmp_path, mocker):
        """Vérifie que list_and_sort_images propage ZipSlipError."""
        mocker.patch(
            "tools.pipeline_core.check_zip_slip",
            side_effect=ZipSlipError("zip-slip simulé"),
        )
        with pytest.raises(ZipSlipError):
            list_and_sort_images(str(tmp_path))


# ---------------------------------------------------------------------------
# build_ocrmypdf_cmd
# ---------------------------------------------------------------------------

class TestBuildOcrmypdfCmd:
    def test_contient_output_type(self):
        cmd = build_ocrmypdf_cmd("in.pdf", "out.pdf")
        assert "--output-type" in cmd
        assert "pdf" in cmd

    def test_contient_lang(self):
        cmd = build_ocrmypdf_cmd("in.pdf", "out.pdf", lang="fra")
        assert "-l" in cmd
        assert "fra" in cmd

    def test_contient_rotate_et_deskew_par_defaut(self):
        cmd = build_ocrmypdf_cmd("in.pdf", "out.pdf")
        assert "--rotate-pages" in cmd
        assert "--deskew" in cmd

    def test_sans_rotate(self):
        cmd = build_ocrmypdf_cmd("in.pdf", "out.pdf", rotate=False)
        assert "--rotate-pages" not in cmd

    def test_chemins_en_dernier(self):
        cmd = build_ocrmypdf_cmd("/a/in.pdf", "/b/out.pdf")
        assert cmd[-2] == "/a/in.pdf"
        assert cmd[-1] == "/b/out.pdf"


# ---------------------------------------------------------------------------
# stable_json / sha256_str
# ---------------------------------------------------------------------------

class TestStableJson:
    def test_cles_triees_deterministe(self):
        """Deux dicts avec les mêmes clés dans un ordre différent → même JSON."""
        assert stable_json({"b": 2, "a": 1}) == stable_json({"a": 1, "b": 2})

    def test_compact_sans_espaces(self):
        result = stable_json({"k": "v"})
        assert " " not in result

    def test_unicode_preserve(self):
        result = stable_json({"lang": "fra+eng"})
        assert "fra+eng" in result

    def test_dict_vide(self):
        assert stable_json({}) == "{}"


class TestSha256Str:
    def test_hash_deterministe(self):
        h1 = sha256_str("hello")
        h2 = sha256_str("hello")
        assert h1 == h2

    def test_longueur_64_caracteres(self):
        assert len(sha256_str("test")) == 64

    def test_hash_different_pour_entrees_differentes(self):
        assert sha256_str("aaa") != sha256_str("bbb")

    def test_coherent_avec_hashlib(self):
        """sha256_str doit produire le même hash que hashlib.sha256 directement."""
        s = "comic2pdf"
        expected = hashlib.sha256(s.encode("utf-8")).hexdigest()
        assert sha256_str(s) == expected


# ---------------------------------------------------------------------------
# make_job_key / output_filename
# ---------------------------------------------------------------------------

class TestMakeJobKey:
    def test_retourne_tuple(self):
        profile_hash, job_key = make_job_key("abc123", "fra+eng")
        assert isinstance(profile_hash, str)
        assert isinstance(job_key, str)
        assert "__" in job_key

    def test_determinisme(self):
        _, jk1 = make_job_key("abc", "fra+eng")
        _, jk2 = make_job_key("abc", "fra+eng")
        assert jk1 == jk2

    def test_langue_normalisee(self):
        _, jk1 = make_job_key("abc", "fra+eng")
        _, jk2 = make_job_key("abc", "eng+fra")
        assert jk1 == jk2

    def test_hash_different_pour_fichiers_differents(self):
        _, jk1 = make_job_key("hash_a", "fra+eng")
        _, jk2 = make_job_key("hash_b", "fra+eng")
        assert jk1 != jk2


class TestOutputFilename:
    def test_format_correct(self):
        name = output_filename("/path/to/MonComic.cbz", "abc123__def456")
        assert name == "MonComic__job-abc123__def456.pdf"

    def test_extension_cbr(self):
        name = output_filename("Comic.cbr", "key123")
        assert name == "Comic__job-key123.pdf"
        assert name.endswith(".pdf")

