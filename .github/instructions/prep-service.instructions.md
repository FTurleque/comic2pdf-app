---
description: Règles de code, tests et architecture pour le service de préparation CBZ/CBR → raw.pdf
applyTo: services/prep-service/**
---

# Instructions — prep-service

## Rôle
Extraire les images d'une archive CBZ/CBR via `7z`, les trier par ordre naturel et les assembler
en `raw.pdf` via `img2pdf`. Expose une API FastAPI HTTP sur le port 8080.

## Structure des fichiers

```
services/prep-service/
├── app/
│   ├── __init__.py
│   ├── core.py      # Fonctions pures testables (filter_images, sort_images, images_to_pdf, get_tool_versions)
│   ├── main.py      # FastAPI app + workers (bootstrap dans @app.on_event("startup"))
│   └── utils.py     # ensure_dir, atomic_write_json, read_json, natural_key, now_iso
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── requirements.txt      # fastapi, uvicorn[standard], img2pdf
└── requirements-dev.txt  # -r requirements.txt + pytest, pytest-cov, pytest-mock, httpx, pillow
```

## API HTTP

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/info` | Versions du service et des outils (`7z`, `img2pdf`) |
| `POST` | `/jobs/prep` | Soumettre un job (body : `jobId`, `inputPath`, `workDir`) → 202 |
| `GET` | `/jobs/{job_id}` | État courant d'un job |

## Règles de code

### Fonctions pures → `core.py`
Toute logique testable indépendamment du serveur va dans `core.py` :

- `filter_images(root: str) -> List[str]`
  Parcourt récursivement `root`. Exclut : parasites (`thumbs.db`, `.DS_Store`, `desktop.ini`),
  dossiers `__MACOSX`, fichiers sans extension image valide
  (`{.jpg, .jpeg, .png, .webp, .tif, .tiff, .bmp}`).

- `sort_images(paths: List[str]) -> List[str]`
  Tri naturel via `natural_key` de `utils.py` sur le basename.
  Garantit `1.jpg < 2.jpg < 10.jpg` (pas lexicographique).

- `images_to_pdf(images: List[str], dest_path: str) -> None`
  Écrit d'abord dans `dest_path + ".tmp"`, puis `os.replace()` atomique.
  Lève `ValueError` si `images` est vide.

- `get_tool_versions() -> dict`
  Clés : `"7z"` (première ligne de la sortie `7z`) et `"img2pdf"` (attribut `__version__`).
  Retourne `"unknown"` en cas d'erreur.

### main.py — séquence `run_job(job_meta_path)`
1. Lire le JSON de métadonnées.
2. Supprimer les artefacts précédents (`pages/`, `raw.tmp.pdf`, `raw.pdf`, `prep.log`).
3. `update_state(..., {"state": "RUNNING", "message": "extracting"})`.
4. Écrire `prep.heartbeat` (`"start"`).
5. Exécuter `7z x -y -o<pages_dir> <input>` via `subprocess.run`.
6. Vérifier `returncode != 0` → `RuntimeError(f"7z failed rc={p.returncode}")`.
7. Écrire `prep.heartbeat` (`"listing_images"`).
8. Appeler `list_and_sort_images(pages_dir)` — lève `RuntimeError` si vide.
9. Écrire `prep.heartbeat` (`"img2pdf"`).
10. Appeler `images_to_pdf(images, raw_tmp)`.
11. `os.replace(raw_tmp, raw_pdf)`.
12. `update_state(..., {"state": "DONE", "artifacts": {"rawPdf": raw_pdf}})`.
13. `except` → `update_state(..., {"state": "ERROR", "message": ..., "error": {...}})` + `raise`.

### Bootstrap (non-impactant à l'import)
```python
@app.on_event("startup")
def startup():
    requeue_running_on_startup()
    for _ in range(max(1, SERVICE_CONCURRENCY)):
        t = threading.Thread(target=worker_loop, args=(_stop_event,), daemon=True)
        t.start()
```
Ne jamais appeler `requeue_running_on_startup()` ou créer des threads en dehors de ce handler.

### Gestion des erreurs
Toute exception dans `run_job` doit :
1. Appeler `update_state` avec `state=ERROR`, `message=str(e)`, `error={"type": ..., "detail": ...}`.
2. Re-lever l'exception (`raise`) pour que `worker_loop` déplace le job vers `ERROR_DIR`.

## Tests

### Exigences absolues
- `subprocess.run` (7z) **toujours mocké** — 7z n'est pas requis sur la machine de test.
- Utiliser `pytest-mock` (`mocker.patch`) ou `unittest.mock.patch`.
- Smoke test `images_to_pdf` : générer des images réelles avec Pillow (`requirements-dev.txt`),
  vérifier que le fichier de sortie commence par `b"%PDF"`.

### Cas minimaux à couvrir (`test_core.py`)

**Tri naturel**
```python
sort_images(["10.jpg", "2.jpg", "1.jpg"]) == ["1.jpg", "2.jpg", "10.jpg"]
sort_images(["003.png", "001.png", "010.png"]) == ["001.png", "003.png", "010.png"]
```

**Filtrage**
- `thumbs.db`, `.DS_Store`, `desktop.ini` → exclus.
- Dossier `__MACOSX/` → ignoré (ne pas descendre dedans).
- Fichiers `.txt`, `.xml` → exclus.
- Images dans sous-dossiers → incluses (récursif).

**Smoke test PDF**
```python
# Pillow génère 2 images PNG de test
images_to_pdf([img1, img2], dest)
assert open(dest, "rb").read(4) == b"%PDF"
```

**Cas d'erreur**
```python
images_to_pdf([], dest)  # → ValueError
images_to_pdf(["not_an_image.jpg"], dest)  # → Exception
```

### Lancer les tests
```powershell
cd services\prep-service
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

## Anti-patterns

- ❌ Ne pas appeler `requeue_running_on_startup()` à l'import du module.
- ❌ Ne pas invoquer `7z` ou `img2pdf` dans les tests unitaires.
- ❌ Ne pas utiliser de chemins hardcodés — toujours construire depuis `DATA_DIR`.
- ❌ Ne pas écrire directement dans `raw.pdf` — toujours passer par `raw.tmp.pdf` + `os.replace()`.
- ❌ Ne pas modifier `utils.py` sans mettre à jour les copies dans `ocr-service` et `orchestrator`.

