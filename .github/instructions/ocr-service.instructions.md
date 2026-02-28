---
description: Règles de code, tests et architecture pour le service OCR raw.pdf → final.pdf
applyTo: services/ocr-service/**
---

# Instructions — ocr-service

## Rôle
Appliquer l'OCR sur `raw.pdf` via `ocrmypdf` (Tesseract + Ghostscript) et produire `final.pdf`
avec texte sélectionnable. Expose une API FastAPI HTTP sur le port 8080.

## Structure des fichiers

```
services/ocr-service/
├── app/
│   ├── __init__.py
│   ├── core.py      # get_tool_versions, build_ocrmypdf_cmd, requeue_running
│   ├── main.py      # FastAPI app + workers
│   └── utils.py     # ensure_dir, atomic_write_json, read_json, sha256_file, now_iso
├── tests/
│   ├── __init__.py
│   ├── test_core.py  # Versions outils, construction commande, requeue
│   └── test_jobs.py  # run_job OK/ERROR (subprocess mocké)
├── requirements.txt      # fastapi, uvicorn[standard], ocrmypdf
└── requirements-dev.txt  # -r requirements.txt + pytest, pytest-cov, pytest-mock, httpx
```

## API HTTP

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/info` | Versions du service et des outils (`ocrmypdf`, `tesseract`, `ghostscript`) |
| `POST` | `/jobs/ocr` | Soumettre un job (body JSON complet) → 202 |
| `GET` | `/jobs/{job_id}` | État courant d'un job |

### Body `POST /jobs/ocr`
```json
{
  "jobId": "string",
  "rawPdfPath": "string",
  "workDir": "string",
  "lang": "fra+eng",
  "rotatePages": true,
  "deskew": true,
  "optimize": 1
}
```

## Règles de code

### Fonctions pures → `core.py`

- `get_tool_versions() -> dict`
  Clés obligatoires : `"ocrmypdf"`, `"tesseract"`, `"ghostscript"`.
  Commandes : `ocrmypdf --version`, `tesseract --version`, `gs --version`.
  Retourne `"unknown"` si l'outil est absent (`FileNotFoundError`).
  Lire la **première ligne** de `stdout` ou `stderr` selon l'outil.

- `build_ocrmypdf_cmd(raw_pdf, dest, *, lang, rotate, deskew, optimize) -> List[str]`
  Construction de la liste de tokens :
  - Commence toujours par `["ocrmypdf", "--output-type", "pdf"]`.
  - `rotate=True` → ajoute `"--rotate-pages"`.
  - `deskew=True` → ajoute `"--deskew"`.
  - `optimize` → ajoute `["--optimize", str(optimize)]`.
  - `lang` → ajoute `["-l", lang]`.
  - `raw_pdf` et `dest` sont **toujours les deux derniers arguments**.

- `requeue_running(running_dir, queue_dir) -> int`
  Déplace tous les `.json` de `running_dir` vers `queue_dir` via `os.replace()`.
  Ignore les fichiers non-`.json`.
  Retourne le nombre de jobs remis en file.

### main.py — séquence `run_job(job_meta_path)`
1. Lire le JSON de métadonnées.
2. Supprimer les artefacts précédents (`final.tmp.pdf`, `final.pdf`, `ocr.log`).
3. `update_state(..., {"state": "RUNNING", "message": "ocr running"})`.
4. Écrire `ocr.heartbeat` (`"start"`).
5. Appeler `build_ocrmypdf_cmd(raw_pdf, final_tmp, ...)`.
6. Exécuter via `subprocess.run(cmd, capture_output=True, text=True)`.
7. Vérifier `returncode != 0` → `RuntimeError(f"ocrmypdf failed rc={p.returncode}")`.
8. `os.replace(final_tmp, final_pdf)`.
9. `update_state(..., {"state": "DONE", "artifacts": {"finalPdf": final_pdf}})`.
10. `except` → `update_state(..., {"state": "ERROR", ...})` + `raise`.

### Paramètres OCR (lus depuis le job meta JSON)
- `lang` : défaut `"fra+eng"`.
- `rotatePages` : défaut `True`.
- `deskew` : défaut `True`.
- `optimize` : défaut `1`.

### Bootstrap
```python
@app.on_event("startup")
def startup():
    requeue_running(RUNNING_DIR, QUEUE_DIR)
    for _ in range(max(1, SERVICE_CONCURRENCY)):
        t = threading.Thread(target=worker_loop, args=(_stop_event,), daemon=True)
        t.start()
```

### Rename atomique obligatoire
```python
os.replace(final_tmp, final_pdf)   # ← jamais écrire directement dans final.pdf
```
Après succès, `final.tmp.pdf` ne doit plus exister.

## Tests

### Exigences absolues
- `subprocess.run` (ocrmypdf) **toujours mocké** — Tesseract et Ghostscript non requis.
- Le mock doit simuler la **création** du fichier `final.tmp.pdf` (ocrmypdf écrit ce fichier).

### Cas minimaux — `test_core.py`

**`get_tool_versions`**
```python
# Mock subprocess.run → retourner des versions factices
versions = get_tool_versions()
assert "ocrmypdf" in versions
assert "tesseract" in versions
assert "ghostscript" in versions
# Outil absent → "unknown"
```

**`build_ocrmypdf_cmd`**
```python
cmd = build_ocrmypdf_cmd("/in/raw.pdf", "/out/final.pdf")
assert "--rotate-pages" in cmd   # rotate=True par défaut
assert "--deskew" in cmd
assert cmd[-2] == "/in/raw.pdf"
assert cmd[-1] == "/out/final.pdf"

cmd = build_ocrmypdf_cmd(..., rotate=False)
assert "--rotate-pages" not in cmd
```

**`requeue_running`**
```python
# 3 .json dans running/ → déplacés en queue/
count = requeue_running(str(running_dir), str(queue_dir))
assert count == 3
# .txt ignoré
```

### Cas minimaux — `test_jobs.py`

**Job OK**
```python
def fake_run(cmd, **kwargs):
    open(final_tmp_path, "wb").write(b"%PDF-1.4 ocr")
    return MagicMock(returncode=0, stdout="", stderr="")

mocker.patch("subprocess.run", side_effect=fake_run)
run_job(meta_path)
meta = read_json(meta_path)
assert meta["state"] == "DONE"
assert os.path.exists(os.path.join(job_dir, "final.pdf"))
```

**Job ERROR**
```python
mocker.patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="err"))
with pytest.raises(RuntimeError):
    run_job(meta_path)
meta = read_json(meta_path)
assert meta["state"] == "ERROR"
assert meta["error"]["type"] == "RuntimeError"
```

### Lancer les tests
```powershell
cd services\ocr-service
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

## Anti-patterns

- ❌ Ne pas exécuter ocrmypdf, tesseract ou ghostscript dans les tests unitaires.
- ❌ Ne pas écrire directement dans `final.pdf` — toujours passer par `final.tmp.pdf` + `os.replace()`.
- ❌ Ne pas hardcoder la langue OCR — la lire depuis le job meta JSON.
- ❌ Ne pas modifier `prep-service` en intervenant dans `ocr-service`.
- ❌ Ne pas appeler de services HTTP externes autres que ceux définis dans `PREP_URL`/`OCR_URL`.

