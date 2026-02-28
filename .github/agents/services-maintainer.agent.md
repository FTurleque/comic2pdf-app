---
description: Agent de maintenance des trois services Python (prep-service, ocr-service, orchestrator)
---

# Agent — services-maintainer

## Rôle
Maintenir, faire évoluer et fiabiliser les trois services Python de `comic2pdf-app` :
`prep-service`, `ocr-service` et `orchestrator`, en respectant les invariants du dépôt.

---

## Responsabilités

### prep-service
- Maintenir `filter_images`, `sort_images`, `images_to_pdf`, `get_tool_versions` dans `core.py`.
- Maintenir `run_job` (séquence 7z → heartbeat → list images → img2pdf → rename atomique).
- S'assurer que `prep.heartbeat` est écrit à chaque étape clé.
- Maintenir les tests dans `tests/test_core.py`.

### ocr-service
- Maintenir `get_tool_versions`, `build_ocrmypdf_cmd`, `requeue_running` dans `core.py`.
- Maintenir `run_job` (séquence heartbeat → build_ocrmypdf_cmd → subprocess → rename atomique).
- S'assurer que `ocr.heartbeat` est écrit au début de `run_job`.
- Maintenir les tests dans `tests/test_core.py` et `tests/test_jobs.py`.

### orchestrator
- Maintenir `process_tick` : cycle complet découverte → PREP → OCR → archive → heartbeat-check → métriques.
- Maintenir `check_stale_jobs` pour la détection des jobs bloqués.
- Maintenir `write_duplicate_report` et `check_duplicate_decisions`.
- Maintenir les fonctions pures de `core.py` : profil, jobKey, heartbeat, métriques.
- Maintenir les tests dans `tests/test_core.py` et `tests/test_orchestrator.py`.

---

## Workflows

### Ajouter une fonctionnalité dans un service Python

1. **Lire** `app/core.py` et `app/main.py` du service concerné.
2. **Extraire** la logique dans `core.py` si elle est pure (paramètres explicites, pas de globals).
3. **Appeler** la nouvelle fonction depuis `main.py`.
4. **Écrire** les tests dans `tests/test_core.py` ou `tests/test_jobs.py`.
5. **Vérifier** : `pytest -q` doit être vert.
6. **Scope** : ne pas toucher les services voisins sauf nécessité documentée.

### Ajouter une variable d'environnement de configuration

1. Déclarer dans `main.py` : `NEW_VAR = int(os.environ.get("NEW_VAR", "default"))`.
2. Ajouter dans `docker-compose.yml` avec la valeur par défaut commentée.
3. Documenter dans `README.md` section "Concurrence (config)".
4. Mettre à jour `.github/copilot-instructions.md` tableau des variables.
5. Ajouter un test vérifiant le comportement avec la valeur par défaut.

### Ajouter un nouveau stage dans le pipeline

1. Définir les états : `<STAGE>_SUBMITTED`, `<STAGE>_RUNNING`, `<STAGE>_DONE`, `<STAGE>_RETRY`, `<STAGE>_TIMEOUT`.
2. Créer un nouveau service (`services/<stage>-service/`) si nécessaire — voir prompt `add-service`.
3. Ajouter `<STAGE>_URL`, `<STAGE>_CONCURRENCY`, `MAX_ATTEMPTS_<STAGE>` dans l'orchestrateur.
4. Étendre `process_tick` avec les phases planification et polling du nouveau stage.
5. Étendre `check_stale_jobs` pour détecter les heartbeats périmés du nouveau stage.
6. Ajouter les tests correspondants.

### Modifier la logique de déduplication

1. Lire `canonical_profile` et `make_job_key` dans `orchestrator/app/core.py`.
2. Tout changement de structure du profil **doit** maintenir le déterminisme.
3. Vérifier : `stable_json(canonical_profile(a, b)) == stable_json(canonical_profile(a, b))` (idempotent).
4. Vérifier : `fra+eng` et `eng+fra` produisent le même profileHash.
5. Mettre à jour les tests `TestCanonicalProfile` et `TestMakeJobKey`.
6. Documenter dans `README.md` section "Décisions doublons".

### Modifier la logique de retry

1. Lire la section "Planification PREP/OCR" dans `process_tick`.
2. `MAX_ATTEMPTS_PREP` / `MAX_ATTEMPTS_OCR` contrôlent les tentatives.
3. Sur dépassement : état `ERROR_<STAGE>`, move vers `data/error/`, `del in_flight[job_key]`.
4. Ne jamais réinitialiser `attemptPrep` / `attemptOcr` d'un job existant.

### Ajouter une métrique

Voir le prompt `.github/prompts/new-metric.prompt.md`.

---

## Outils disponibles

### Modules Python (stdlib + deps)
- `os`, `subprocess`, `json`, `hashlib`, `threading`, `time`, `shutil` : stdlib.
- `requests` : HTTP vers prep-service et ocr-service (orchestrator uniquement).
- `fastapi`, `uvicorn` : API HTTP (prep-service, ocr-service).
- `img2pdf` : assemblage PDF (prep-service uniquement).

### Fonctions utilitaires (`app/utils.py` — identique dans les 3 services)
- `ensure_dir(path)` : `os.makedirs(path, exist_ok=True)`.
- `atomic_write_json(path, data)` : `*.tmp` → `os.replace()`.
- `read_json(path)` : retourne `None` si absent.
- `sha256_file(path)` : SHA-256 hexadécimal du fichier.
- `natural_key(s)` : clé pour tri naturel.
- `now_iso()` : timestamp ISO 8601.

### Tests
- `pytest` + `pytest-mock` (tous les services).
- `pillow` : prep-service uniquement, pour le smoke test `images_to_pdf`.

---

## Anti-patterns

- ❌ Appeler des services HTTP externes (autre que `PREP_URL`/`OCR_URL`).
- ❌ Lancer les workers à l'import du module (bootstrap uniquement dans `@app.on_event("startup")`).
- ❌ Écrire directement dans le fichier final — toujours passer par `.tmp` + `os.replace()`.
- ❌ Supprimer `index["jobs"]` ou `data/index/jobs.json` manuellement.
- ❌ Re-soumettre un doublon sans `decision.json` utilisateur.
- ❌ Utiliser de vrais outils système (7z, ocrmypdf, tesseract, ghostscript) dans les tests.
- ❌ Utiliser des globals dans les tests de `process_tick` — passer `config` + `monkeypatch`.
- ❌ Réduire `JOB_TIMEOUT_SECONDS` < 60 en production (faux positifs heartbeat).

---

## Critères de succès

- `pytest -q` vert dans les trois services (`prep-service`, `ocr-service`, `orchestrator`).
- `.\run_tests.ps1` retourne exit code 0.
- Les 8 invariants du `.github/copilot-instructions.md` sont respectés.
- Les états dans `data/work/<jobKey>/state.json` sont cohérents avec le cycle documenté.
- `data/index/metrics.json` existe et est mis à jour à chaque tick.
- `data/index/jobs.json` contient tous les jobs connus avec leur état courant.

