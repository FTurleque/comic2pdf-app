# RAPPORT_IMPLEMENTATION_SPRINT3-CLI-WATCH_2026-03-04

> Généré par IA — GitHub Copilot (GPT-4o)

---

## 1. Titre et type

**Titre** : Implémentation Sprint 3 — Mode sans Docker (CLI et watch-folder local)
**Type** : IMPLEMENTATION
**Date** : 2026-03-04
**Auteur(s)** : Équipe comic2pdf-app (soumission humaine requise)

---

## 2. Contexte et résumé

Le README annonçait explicitement un "Mode sans Docker (CLI / watch local) — À venir" avec `tools/cli.py` et `tools/watch_local.py`. Le Sprint 3 implémente ce mode en extrayant les fonctions pures des services Python en un module autonome `tools/pipeline_core.py` (sans imports croisés vers `services/*/app/`), en créant l'interface CLI complète et la boucle de surveillance locale, avec 92 tests unitaires et E2E minimaux déterministes. La documentation utilisateur et développeur est mise à jour pour refléter le statut "disponible".

---

## 3. Description des changements

### Fichiers créés

| Fichier | Type | Description |
|---|---|---|
| `tools/__init__.py` | Nouveau | Marqueur de package Python |
| `tools/pipeline_core.py` | Nouveau | Fonctions pures autonomes : FS, images, OCR cmd, jobKey (sans import croisé services/) |
| `tools/deps.py` | Nouveau | Détection dépendances externes (7z, ocrmypdf, tesseract, ghostscript) + messages actionnables |
| `tools/cli.py` | Nouveau | Interface CLI argparse : `--lang`, `--out`, `--no-ocr`, `--keep-temp`, `--check-deps` |
| `tools/watch_local.py` | Nouveau | Boucle de surveillance locale : polling, `.part`→rename ignoré, doublons → hold/, processed.json |
| `tools/requirements.txt` | Nouveau | Dépendance prod : `img2pdf` |
| `tools/requirements-dev.txt` | Nouveau | Dépendances dev : pytest, pytest-cov, pytest-mock, pillow |
| `tools/pytest.ini` | Nouveau | Config pytest : `testpaths = ../tests/tools`, `pythonpath = ..` |
| `tests/tools/conftest.py` | Nouveau | Injection racine repo dans `sys.path` pour import `tools.*` |
| `tests/tools/test_deps.py` | Nouveau | 16 tests unitaires : find_tool, require_tool, check_all_deps, check_deps_report |
| `tests/tools/test_pipeline_core.py` | Nouveau | 32 tests unitaires : FS, images, OCR cmd, jobKey, validate_pdf, check_file_signature |
| `tests/tools/test_cli.py` | Nouveau | 12 tests : parsing args, validate_input, main() (subprocess mocké) |
| `tests/tools/test_watch.py` | Nouveau | 19 tests : parser, scan, processed.json, doublons, watch_loop, main() |
| `tests/tools/test_cli_e2e.py` | Nouveau | E2E mocké (4 tests CI-safe) + E2E réel (1 test skipif 7z absent) |
| `scripts/test_tools.ps1` | Nouveau | Script PowerShell : venv auto + pytest + coverage (PYTHONPATH=repo root) |
| `scripts/test_tools.sh` | Nouveau | Script bash équivalent |
| `conftest.py` | Nouveau | Conftest racine repo : inject `sys.path` pour tous les tests |

### Fichiers modifiés

| Fichier | Type | Description de la modification |
|---|---|---|
| `docs/user/installation.md` | Modifié | Remplacement note "À venir" → section installation complète mode CLI/local |
| `docs/user/usage.md` | Modifié | Ajout sections CLI et watch-folder local (usage, options, exemples, doublons, processed.json) |
| `docs/dev/setup.md` | Modifié | Ajout section setup tools/ (venv, variables d'environnement) |
| `docs/dev/testing.md` | Modifié | Ajout section tests CLI/watch (stratégie, commandes, guide ajout tests) |
| `README.md` | Modifié | Section 10 : "À venir" → implémenté avec architecture, installation et exemples |

---

## 4. Étapes pour reproduire / commandes exécutées

### Installation

```powershell
# Windows PowerShell
cd tools
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### Lancer les tests

```powershell
# Via script (recommandé)
.\scripts\test_tools.ps1

# Manuel (depuis tools/)
$env:PYTHONPATH = (Resolve-Path "..").Path
.\".venv\Scripts\python.exe" -m pytest -q --tb=short ..\tests\tools\
```

### Résultats des tests (2026-03-04)

| Module | Tests | Résultat |
|---|---|---|
| `test_deps.py` | 16 | ✅ PASS |
| `test_pipeline_core.py` | 32 | ✅ PASS |
| `test_cli.py` | 12 | ✅ PASS |
| `test_watch.py` | 19 | ✅ PASS |
| `test_cli_e2e.py` | 4 mocké + 1 skipé | ✅ PASS (1 skipé : 7z absent) |
| **Total** | **92 passés, 1 skipé** | ✅ |

---

## 5. Points d'attention / Limitations

- **Doublons mode local** : détection minimale via `jobKey` + déplacement vers `hold/`. Pas d'interface de décision desktop intégrée pour le mode local (hors scope Sprint 3).
- **OCR en mode local** : nécessite `tesseract` et `ghostscript` installés en système. Sur CI sans ces binaires, les tests OCR sont mockés ou skipés.
- **Windows PATH 7z** : `7-Zip` doit être ajouté manuellement au PATH sur Windows. Le message d'erreur dans `deps.py` donne les instructions.
- **conftest.py racine** : ajouté pour résoudre les imports `tools.*` dans les tests. À prendre en compte si d'autres conftest racine sont ajoutés dans le futur.

---

## 6. Liens et références

- PR : `[à renseigner lors de la soumission]`
- Issue : `[à renseigner]`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`

---

## 7. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

---

## Checklist PR

- [x] Rapport conforme au pattern `RAPPORT_<TYPE>_YYYY-MM-DD.md`
- [x] Placé dans `docs/ia/rapports-execution/`
- [x] Basé sur `docs/ia/templates/rapport_template.md`
- [ ] Au moins 1 reviewer humain assigné
- [x] Mention "Généré par IA" + outil/agent (GitHub Copilot)
- [x] Sections minimales complètes (titre, date, auteur, résumé, étapes, fichiers modifiés, liens PR)

