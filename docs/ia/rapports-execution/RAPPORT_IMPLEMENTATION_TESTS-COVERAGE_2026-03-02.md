# RAPPORT_IMPLEMENTATION_TESTS-COVERAGE_2026-03-02

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `Équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Standardisation de la stratégie de tests et couverture Python + Java |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-03-02` |
| **Auteur(s)** | Équipe comic2pdf-app |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | — |

---

## 2. Contexte et résumé

Le projet `comic2pdf-app` disposait de tests unitaires fonctionnels mais sans configuration pytest standardisée, sans scripts de test dédiés par service, et sans génération systématique de rapports de couverture. Le runner global `run_tests.ps1` contenait toute la logique de manière monolithique. Cette implémentation ajoute une stratégie de tests standardisée : `pytest.ini` par service, 8 scripts individuels (PowerShell + Bash), 2 scripts globaux `test_all`, et transforme `run_tests.ps1` en wrapper backward-compatible. Elle met également à jour la documentation et le `.gitignore`.

---

## 3. Description des changements

### Fichiers créés

| Fichier | Type | Description |
|---|---|---|
| `services/prep-service/pytest.ini` | Nouveau | Configuration pytest minimale : `testpaths = tests` |
| `services/ocr-service/pytest.ini` | Nouveau | Configuration pytest minimale : `testpaths = tests` |
| `services/orchestrator/pytest.ini` | Nouveau | Configuration pytest minimale : `testpaths = tests` |
| `scripts/test_prep.ps1` | Nouveau | Tests + coverage prep-service (PowerShell) : venv auto, pytest + rapports |
| `scripts/test_ocr.ps1` | Nouveau | Tests + coverage ocr-service (PowerShell) |
| `scripts/test_orchestrator.ps1` | Nouveau | Tests + coverage orchestrator (PowerShell) |
| `scripts/test_desktop.ps1` | Nouveau | `mvn test` desktop-app (PowerShell), option `-Ui` pour profil `ui-tests` |
| `scripts/test_prep.sh` | Nouveau | Tests + coverage prep-service (Bash) : venv auto, pytest + rapports |
| `scripts/test_ocr.sh` | Nouveau | Tests + coverage ocr-service (Bash) |
| `scripts/test_orchestrator.sh` | Nouveau | Tests + coverage orchestrator (Bash) |
| `scripts/test_desktop.sh` | Nouveau | `mvn test` desktop-app (Bash), option `--ui` |
| `scripts/test_all.ps1` | Nouveau | Runner global officiel (PowerShell) : 4 étapes, stop immédiat par défaut, `-ContinueOnError` opt-in, résumé coloré |
| `scripts/test_all.sh` | Nouveau | Runner global officiel (Bash) : même logique, `--continue-on-error` opt-in |

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `run_tests.ps1` | Modifié | Transformé en wrapper backward-compatible : délègue à `scripts/test_all.ps1 @args` |
| `.gitignore` | Modifié | Ajout section *Coverage Python par service* : `services/**/coverage.xml`, `services/**/htmlcov/`, `services/**/.coverage` |
| `docs/dev/testing.md` | Modifié | Refonte : suppression compteurs figés, ajout sections *Scripts par service*, *Coverage Python*, *Scripts globaux*, mise à jour tableau vue d'ensemble |

### Outputs de couverture générés par service (ignorés par Git)

| Service | XML | HTML |
|---|---|---|
| `prep-service` | `services/prep-service/coverage.xml` | `services/prep-service/htmlcov/index.html` |
| `ocr-service` | `services/ocr-service/coverage.xml` | `services/ocr-service/htmlcov/index.html` |
| `orchestrator` | `services/orchestrator/coverage.xml` | `services/orchestrator/htmlcov/index.html` |
| `desktop-app` | `desktop-app/target/site/jacoco/` | `desktop-app/target/site/jacoco/index.html` |

---

## 4. Étapes pour reproduire / commandes exécutées

### Lancer tous les tests (point d'entrée officiel)

```powershell
# Windows PowerShell — depuis la racine du dépôt
.\scripts\test_all.ps1

# Avec résumé complet même en cas d'échec intermédiaire
.\scripts\test_all.ps1 -ContinueOnError
```

```bash
# Linux / macOS
./scripts/test_all.sh
./scripts/test_all.sh --continue-on-error
```

### Lancer les tests d'un service isolé

```powershell
.\scripts\test_prep.ps1
.\scripts\test_ocr.ps1
.\scripts\test_orchestrator.ps1
.\scripts\test_desktop.ps1          # sans UI (défaut)
.\scripts\test_desktop.ps1 -Ui      # avec tests TestFX
```

```bash
./scripts/test_prep.sh
./scripts/test_ocr.sh
./scripts/test_orchestrator.sh
./scripts/test_desktop.sh
./scripts/test_desktop.sh --ui
```

### Alias backward-compatible (inchangé pour les utilisateurs existants)

```powershell
.\run_tests.ps1
.\run_tests.ps1 -ContinueOnError
```

### Consulter les rapports de couverture HTML

```powershell
# Ouvrir le rapport prep-service
Start-Process "services\prep-service\htmlcov\index.html"
# Rapport JaCoCo Java
Start-Process "desktop-app\target\site\jacoco\index.html"
```

---

## 5. Points d'attention / Limitations

- Les scripts PowerShell individuels (`test_prep.ps1` etc.) utilisent `exit $LASTEXITCODE` dans un bloc `try/finally`. Sur PowerShell 5.1, `exit` dans un `finally` est bien propagé vers l'appelant.
- Le venv est créé avec `py -3` sur Windows si `py` est disponible, sinon fallback `python`. Sur Linux/macOS, `python3` est utilisé directement. Si plusieurs versions Python coexistent, s'assurer que `py -3` ou `python3` pointe vers Python 3.12+.
- Les rapports de couverture Python (`coverage.xml`, `htmlcov/`) sont générés dans le dossier de chaque service. Ils sont ignorés par Git grâce aux patterns ajoutés dans `.gitignore`.
- Les tests UI TestFX (`-Ui` / `--ui`) ne font pas partie du run global par défaut. Ils nécessitent un écran (ou Monocle headless) et sont opt-in via `scripts/test_desktop.ps1 -Ui`.

---

## 6. Liens et références

- PR : —
- Issue : —
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`
- Documentation tests mise à jour : `docs/dev/testing.md`
- Runner global : `scripts/test_all.ps1`, `scripts/test_all.sh`

---

## 7. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

