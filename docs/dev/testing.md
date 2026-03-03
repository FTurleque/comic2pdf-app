# Tests — comic2pdf-app

Ce guide détaille la stratégie de test, les commandes à exécuter et la façon d'ajouter de nouveaux tests.

---

## Vue d'ensemble des tests

| Module | Framework | Fichiers de test |
|---|---|---|
| `prep-service` | pytest | `test_core.py`, `test_security.py` |
| `ocr-service` | pytest | `test_core.py`, `test_jobs.py` |
| `orchestrator` | pytest | `test_core.py`, `test_orchestrator.py`, `test_robustness.py`, `test_http_server.py`, `test_logger.py`, `test_auth.py`, `test_safe_path.py` |
| `desktop-app` | JUnit 5 | `ConfigServiceTest.java`, `DuplicateServiceTest.java`, `OrchestratorClientTest.java` |

> **Compteurs de tests** : les totaux évoluent à chaque ajout. Exécuter `scripts/test_all.ps1`
> (ou `scripts/test_all.sh`) et vérifier un exit code `0` pour confirmer que tous les tests passent.

---

## Scripts de test par service

Chaque service dispose de scripts dédiés qui gèrent automatiquement le venv, l'installation des dépendances et la génération des rapports de couverture.

### prep-service

```powershell
# Windows PowerShell
.\scripts\test_prep.ps1
```

```bash
# Linux / macOS
./scripts/test_prep.sh
```

### ocr-service

```powershell
.\scripts\test_ocr.ps1
```

```bash
./scripts/test_ocr.sh
```

### orchestrator

```powershell
.\scripts\test_orchestrator.ps1
```

```bash
./scripts/test_orchestrator.sh
```

> **Venv automatique** : si `.venv` est absent dans le dossier du service, le script le crée
> (`py -3` sur Windows, `python3` sur Linux/macOS). Le Python du venv est utilisé directement
> via son chemin absolu (`.venv/Scripts/python.exe` / `.venv/bin/python`).

---

## Rapports de couverture Python

Chaque script de service génère trois sorties dans le dossier du service :

| Sortie | Emplacement | Usage |
|---|---|---|
| Terminal | stdout | Aperçu rapide des lignes non couvertes |
| XML | `services/<service>/coverage.xml` | Intégration CI (Codecov, SonarQube, etc.) |
| HTML | `services/<service>/htmlcov/index.html` | Navigation locale détaillée |

> Ces fichiers sont ignorés par Git (`.gitignore` — patterns `services/**/coverage.xml`
> et `services/**/htmlcov/`).

---

## Seuils de couverture et stratégie progressive

### Baseline et seuils CI (Sprint 2 — 2026-03-04)

| Service | Baseline Sprint 1 | Seuil CI Sprint 2 | Objectif baseline−2 | Cible T2 2026 |
|---------|------------------|-------------------|---------------------|---------------|
| **prep-service** | 85.30% | **80%** | 83% | 70% |
| **ocr-service** | 88.52% | **83%** | 86% | 70% |
| **orchestrator** | 66.36% | **61%** | 64% | 70% |

> **Tolérance initiale baseline−5** : les seuils CI Sprint 2 (80/83/61%) sont volontairement
> 5 points sous la baseline pour absorber les variations légitimes. Une fois la CI stable,
> ouvrir la PR `chore/coverage-thresholds-sprint2-stable` pour monter aux seuils baseline−2
> (83/86/64%) et mettre à jour `ci.yml` + ce fichier simultanément.

### Différence local vs CI

| Contexte | Seuil | Source |
|----------|-------|--------|
| **Local** (`scripts/test_*.ps1` / `test_*.sh`) | 60% (défaut) | Variable `PY_COV_MIN` (modifiable) |
| **CI GitHub Actions** | 80 / 83 / 61% | Hardcodé dans la matrice `include` de `ci.yml` |

> En local, le seuil 60% est un filet de sécurité minimal. La CI applique les vraies baselines
> mesurées au Sprint 1 pour garantir l'anti-régression.

### Configuration du seuil local

#### Via variable d'environnement (méthode recommandée)

```powershell
# Windows PowerShell
$env:PY_COV_MIN=65
.\scripts\test_prep.ps1
```

```bash
# Linux / macOS
PY_COV_MIN=65 ./scripts/test_prep.sh
```

#### Via paramètre de script (PowerShell uniquement)

```powershell
.\scripts\test_prep.ps1 -CovMin 65
.\scripts\test_ocr.ps1 -CovMin 70
.\scripts\test_orchestrator.ps1 -CovMin 60
```

#### Seuil par défaut

Si `PY_COV_MIN` n'est pas défini : **60%** (phase 1).

### Rapports détaillés

Chaque exécution génère :
1. **Terminal** : Résumé + lignes non couvertes (stdout)
2. **`coverage.xml`** : Format Cobertura pour CI/CD
3. **`htmlcov/index.html`** : Navigation interactive (détails ligne par ligne)

#### Exemple de sortie terminal

```
---------- coverage: platform win32, python 3.13.7 -----------
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
app\__init__.py             0      0   100%
app\core.py               122     22    82%   45-52, 78-81, 115-120
app\main.py               131     63    52%   89-105, 138-174, 210-235
app\utils.py               19     9     53%   28-31, 40-44
-----------------------------------------------------
TOTAL                     279    129    54%

Coverage failure: total of 54% is below --cov-fail-under=60%
```

> L'échec **bloque le build** : exit code ≠ 0. C'est voulu pour garantir la qualité.

### Zones à améliorer en priorité

| Service | Fichier | Couverture actuelle | Raison de faible couverture |
|---------|---------|--------------------|-----------------------------|
| **prep-service** | `main.py` | 52.29% | Logique startup/worker peu testée |
| **prep-service** | `utils.py` | 52.63% | Fonctions utilitaires (sha256, list_images) non testées |
| **prep-service** | `logger.py` | 0% | Module logger non couvert (tests API mockent worker_loop) |
| **ocr-service** | `main.py` | ~50% | Logique startup/worker peu testée |
| **ocr-service** | `logger.py` | 0% | Module logger non couvert |
| **orchestrator** | `main.py` | 23.94% | Boucle principale non testée (par design : tests sur `process_tick`) |
| **orchestrator** | `utils.py` | 77% | Fonctions utilitaires partiellement couvertes |

> **Note** : `main.py` des services FastAPI a une couverture faible car les tests API mockent `worker_loop`.
> Les fonctions pures (`run_job`, `claim_one`) sont testées dans `test_jobs.py` et `test_core.py`.


---

## Tests Python (pytest)

Les scripts ci-dessus exécutent :

```
pytest -q --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    --cov-report=html:htmlcov \
    tests/
```

La configuration pytest de chaque service est dans `pytest.ini` (`testpaths = tests`).
Les options de coverage et de verbosité restent dans les scripts (zéro duplication).

---

## Tests Java (JUnit 5)

```powershell
# Windows PowerShell
cd desktop-app
mvn test
```

```bash
# Linux / macOS
cd desktop-app
mvn test
```

**Résultat attendu** : `BUILD SUCCESS` — voir exit code `0` (le nombre de tests évolue).

> Aucune instance JavaFX n'est démarrée pendant ces tests. Ils portent uniquement sur la logique de service (filesystem, HTTP parsing).

---

## Couverture de code Java (JaCoCo)

### Vue d'ensemble

Le module `desktop-app` utilise **JaCoCo** pour mesurer la couverture de code et imposer des seuils anti-régression.

| Métrique | Phase 1 (actuelle) | Phase 2 (T2 2026) | Phase 3 (T3 2026) |
|----------|-------------------|-------------------|-------------------|
| **LINE** | ≥ 59% (baseline 61%) | ≥ 63% | ≥ 67% |
| **BRANCH** | ≥ 39% (baseline 41%) | ≥ 44% | ≥ 49% |

### Baseline mesurée (module `desktop-app`, 2026-03-03)

- Ligne (LINE) : 241 lignes couvertes / (241 + 558) total = 241 / 799 = 30.16%
- Branches (BRANCH) : 40 branches couvertes / (40 + 190) total = 40 / 230 = 17.39%

> Remarque : ces chiffres viennent du rapport JaCoCo généré localement :
> `desktop-app/target/site/jacoco/jacoco.xml` (et `index.html`).

### Seuils appliqués (Phase 1 - anti-régression)

Conformément à la politique "Option A" (mesurer d'abord, verrouiller ensuite), le profil `coverage-check`
utilise des seuils initiaux calculés à `baseline - 2 points` :

- LINE minimum : 30.16% − 2% → arrondi conservateur = **28%** (0.28)
- BRANCH minimum : 17.39% − 2% → arrondi conservateur = **15%** (0.15)

Ces seuils sont appliqués uniquement via le profil Maven `coverage-check` :

```powershell
# Mesurer la baseline (génère HTML + XML, sans check)
cd desktop-app
mvn -Pcoverage clean verify

# Activer le verrouillage — commande CI standard Sprint 2
cd desktop-app
mvn clean verify -Pcoverage -Pcoverage-check
```

Les rapports JaCoCo produits se trouvent :
- HTML : `desktop-app/target/site/jacoco/index.html`
- XML  : `desktop-app/target/site/jacoco/jacoco.xml`

> Exclusions Phase 1 : `com.comic2pdf.desktop.model.*`, `com.comic2pdf.desktop.ui.controller.*`, `com.comic2pdf.desktop.MainApp` — justifiées (JavaFX glue / getters & setters) ; réévaluer si logique métier ajoutée.

### Tests UI CI — Monocle activé directement (Sprint 2)

Depuis Sprint 2, Monocle est activé **directement** dans la commande CI (plus de commentaire
`# Fallback`). Cette configuration est plus stable en Ubuntu headless.

**Commande CI (`.github/workflows/ci.yml`, job `java-ui-tests`) :**

```bash
xvfb-run -a mvn -q -Pui-tests test \
  -Dtestfx.headless=true \
  -Dprism.order=sw \
  -Dglass.platform=Monocle \
  -Dmonocle.platform=Headless \
  -Dprism.verbose=true
```

**Reproduire en local (Linux/macOS avec Xvfb) :**

```bash
xvfb-run -a mvn -Pui-tests test \
  -Dtestfx.headless=true \
  -Dprism.order=sw \
  -Dglass.platform=Monocle \
  -Dmonocle.platform=Headless
```

**En local Windows (sans Xvfb) :**

```powershell
mvn -Pui-tests test -Dtestfx.headless=true -Dprism.order=sw
# Monocle non requis sur Windows (rendu natif disponible)
```

---

## Scripts globaux — lancer tous les tests

### `scripts/test_all.ps1` (point d'entrée officiel)

```powershell
# Windows PowerShell — depuis la racine du dépôt
.\scripts\test_all.ps1

# Avec résumé complet même en cas d'échec intermédiaire
.\scripts\test_all.ps1 -ContinueOnError
```

### `scripts/test_all.sh` (Linux / macOS)

```bash
./scripts/test_all.sh

# Avec résumé complet
./scripts/test_all.sh --continue-on-error
```

### `run_tests.ps1` (alias backward-compatible)

```powershell
# Depuis la racine — identique à scripts/test_all.ps1
.\run_tests.ps1
```

> `run_tests.ps1` est un alias qui délègue à `scripts/test_all.ps1`. Tous les paramètres
> sont transmis. Préférer `scripts/test_all.ps1` pour les nouveaux usages.

Les scripts globaux :
1. Exécutent chaque script de service individuel (`test_prep`, `test_ocr`, `test_orchestrator`)
2. Exécutent `mvn test` dans `desktop-app/` via `scripts/test_desktop.ps1`
3. S'arrêtent au premier échec par défaut (comportement CI)
4. Affichent un résumé coloré `PASS` / `FAIL` par module
5. Retournent `exit 1` si au moins un module échoue

---


## Stratégie de mock

### Pourquoi mocker `subprocess.run` en Python ?

Les tests unitaires Python ne doivent **pas** dépendre des binaires système (`7z`, `ocrmypdf`, `tesseract`, `ghostscript`). Ces outils :
- Ne sont pas disponibles dans tous les environnements de développement
- Rendraient les tests lents et non déterministes
- Sortent du périmètre des tests unitaires

Tous les appels `subprocess.run` sont mockés avec `pytest-mock` (`mocker.patch`).

### Pourquoi `@TempDir` en Java ?

`@TempDir` (JUnit 5) crée un répertoire temporaire propre pour chaque test, garantissant l'isolation des tests filesystem. Le dossier est automatiquement supprimé à la fin du test.

---

## Fichiers de test et ce qu'ils couvrent

### prep-service — `tests/test_core.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_filter_images_*` | Filtrage des extensions valides (jpg, png, webp, etc.) |
| `test_sort_images_natural` | Tri naturel des noms de fichiers (`page10` après `page9`) |
| `test_images_to_pdf_smoke` | Smoke test : conversion images → PDF (subprocess mocké) |
| `test_list_and_sort_images` | Listing + tri combinés |

### ocr-service — `tests/test_core.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_get_tool_versions` | Récupération des versions ocrmypdf/tesseract (subprocess mocké) |
| `test_build_ocrmypdf_cmd_*` | Construction de la commande ocrmypdf (langues, options) |
| `test_requeue_running` | Remise en queue des jobs RUNNING au démarrage (filesystem réel avec tmpdir) |

### ocr-service — `tests/test_jobs.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_run_job_ok` | Cas nominal : `subprocess.run` réussit, état → DONE |
| `test_run_job_error` | Cas erreur : `subprocess.run` lève une exception, état → ERROR |

### orchestrator — `tests/test_core.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_canonical_profile_*` | Normalisation des langues (`fra+eng` ≡ `eng+fra`) |
| `test_make_job_key` | Génération du jobKey (`fileHash__profileHash`) |
| `test_is_heartbeat_stale` | Détection heartbeat périmé (timestamp + timeout) |
| `test_make_empty_metrics` | Structure initiale des métriques |
| `test_update_metrics` | Incrémentation des compteurs (done, error, running, etc.) |

### orchestrator — `tests/test_orchestrator.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_duplicate_detection` | Détection d'un jobKey existant dans l'index |
| `test_write_duplicate_report` | Écriture du rapport JSON doublon |
| `test_check_duplicate_decisions_*` | Lecture de `decision.json` et exécution des 3 actions |
| `test_check_stale_jobs` | Bascule des jobs périmés en `*_RETRY` (HTTP mocké) |

### orchestrator — `tests/test_robustness.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_validate_pdf_*` | Validation header `%PDF-` + taille minimale |
| `test_check_disk_space_*` | Vérification espace disque (DISK_FREE_FACTOR) |
| `test_check_file_signature_zip` | Magic bytes ZIP (CBZ) |
| `test_check_file_signature_rar` | Magic bytes RAR (CBR) |
| `test_cleanup_old_workdirs` | Suppression workdirs anciens (KEEP_WORK_DIR_DAYS) |
| `test_max_input_size_rejected` | Rejet fichier > MAX_INPUT_SIZE_MB |

### orchestrator — `tests/test_http_server.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_get_metrics` | `GET /metrics` — format JSON et compteurs |
| `test_get_jobs` | `GET /jobs` — liste des jobs |
| `test_get_job_by_key` | `GET /jobs/{jobKey}` — détail, 404 si absent |
| `test_get_config` | `GET /config` — configuration courante |
| `test_post_config` | `POST /config` — patch des clés autorisées |

> Les tests HTTP utilisent un port éphémère pour éviter les conflits.

### orchestrator — `tests/test_logger.py`

| Test | Ce qu'il couvre |
|---|---|
| `test_log_json_format` | Format JSON structuré (champs timestamp, level, service, message) |
| `test_log_json_optional_fields` | Champs optionnels jobKey, stage, attempt présents si fournis |
| `test_log_text_format` | Format texte si `LOG_JSON=false` |

### desktop-app — `ConfigServiceTest.java`

| Test | Ce qu'il couvre |
|---|---|
| `testSaveAndLoad` | Persistance `config.json` (save + load) avec `@TempDir` |
| `testDefaultValues` | Valeurs par défaut si `config.json` absent |
| `testPartialUpdate` | Mise à jour partielle des champs |

### desktop-app — `DuplicateServiceTest.java`

| Test | Ce qu'il couvre |
|---|---|
| `testListDuplicates` | Lecture des rapports JSON dans `reports/duplicates/` |
| `testListDuplicatesEmpty` | Dossier vide → liste vide |
| `testWriteDecision` | Écriture de `decision.json` dans `hold/duplicates/<jobKey>/` |
| `testWriteDecisionAllValues` | Toutes les valeurs de l'enum `DuplicateDecision` |

### desktop-app — `OrchestratorClientTest.java`

| Test | Ce qu'il couvre |
|---|---|
| `testParseJobRow` | Parsing du JSON de réponse `/jobs` |
| `testOfflineBehavior` | Comportement si l'orchestrateur est inaccessible (pas d'exception propagée) |
| `testGetMetrics` | Parsing de la réponse `/metrics` |

---

## Guide : ajouter un nouveau test Python

### Convention

- Un test = une fonction commençant par `test_`
- Toujours : **happy path** + **au moins 1 cas d'erreur**
- Utiliser `pytest-mock` (fixture `mocker`) pour mocker `subprocess.run`

### Exemple : tester une nouvelle fonction `validate_cbz`

```python
# services/orchestrator/tests/test_robustness.py (ou nouveau fichier test_xxx.py)
import pytest
from app.utils import validate_cbz  # exemple


def test_validate_cbz_valid(tmp_path):
    """Happy path : fichier CBZ valide (magic bytes ZIP corrects)."""
    cbz = tmp_path / "comic.cbz"
    cbz.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
    assert validate_cbz(str(cbz)) is True


def test_validate_cbz_invalid_signature(tmp_path):
    """Cas d'erreur : fichier avec signature invalide."""
    bad = tmp_path / "bad.cbz"
    bad.write_bytes(b"\xFF\xFE\xFF\xFE" + b"\x00" * 100)
    assert validate_cbz(str(bad)) is False


def test_validate_cbz_file_not_found():
    """Cas d'erreur : fichier inexistant."""
    assert validate_cbz("/inexistant/fichier.cbz") is False
```

### Exemple : mocker `subprocess.run`

```python
def test_build_and_run_tool(mocker, tmp_path):
    """Tester une fonction qui appelle subprocess.run."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Tool version 1.0\n"

    result = ma_fonction(str(tmp_path / "input.pdf"))

    mock_run.assert_called_once()
    assert result is True
```

---

## Guide : ajouter un nouveau test Java

### Convention

- JUnit 5 uniquement (`org.junit.jupiter.api.*`)
- Utiliser `@TempDir Path tempDir` pour l'isolation filesystem
- Aucun test UI JavaFX (pas de `Platform.runLater` dans les tests)
- Toujours : happy path + au moins 1 cas d'erreur

### Exemple : tester un nouveau service

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

class MonServiceTest {

    @Test
    void testCasNominal(@TempDir Path tempDir) throws Exception {
        // Arrange
        MonService service = new MonService(tempDir);
        Path fichier = tempDir.resolve("test.json");
        fichier.toFile().createNewFile();

        // Act
        boolean result = service.traiter(fichier);

        // Assert
        assertTrue(result, "Le traitement nominal doit réussir");
    }

    @Test
    void testFichierAbsent(@TempDir Path tempDir) {
        // Arrange
        MonService service = new MonService(tempDir);
        Path inexistant = tempDir.resolve("nexiste_pas.json");

        // Act + Assert
        assertFalse(service.traiter(inexistant), "Doit retourner false si fichier absent");
    }
}
```

---

> **Licences** : les outils système requis en production Docker (Ghostscript AGPL-3.0, Tesseract Apache-2.0,
> 7-Zip/p7zip-full) **ne sont pas nécessaires pour les tests** (subprocess entièrement mocké).
> Pour les obligations de licence lors d'une distribution, voir [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).

---

## Retour

[← Retour à la documentation développeur](README.md)

---

# Baseline couverture (Sprint 1)

Cette section décrit comment mesurer la baseline de couverture des tests pour le Sprint 1.

Scope
-----
- Tests API d'intégration ajoutés pour : `services/prep-service` et `services/ocr-service`.
- `orchestrator` n'est pas couvert par des tests API dans ce sprint (script/test-only).

Règles importantes
------------------
- Isolation FS : chaque test API force `DATA_DIR` vers un répertoire temporaire (`tmp_path`) via `monkeypatch.setenv("DATA_DIR", tmp_path)` ou fixture autouse.
- Désactivation des workers en tests : les handlers startup des services respectent la variable d'environnement `DISABLE_WORKERS`. Les tests définissent `DISABLE_WORKERS=1` pour éviter de lancer des threads en arrière-plan.
- Pas d'outils système requis : tous les appels à `subprocess.run` (7z, ocrmypdf, tesseract, ghostscript) sont mockés dans les tests.

Commandes PowerShell — exécuter localement
------------------------------------------
# prep-service
cd services\prep-service ; pytest --cov=app --cov-report=term --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q

# ocr-service
cd services\ocr-service ; pytest --cov=app --cov-report=term --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q

# (optionnel) orchestrator
cd services\orchestrator ; pytest --cov=app --cov-report=term --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q

# JaCoCo — desktop-app (baseline report only, pas de seuil)
cd desktop-app ; mvn -q clean verify
# Alternative (report-only si le plugin n'est pas configuré dans le POM):
cd desktop-app ; mvn -q test org.jacoco:jacoco-maven-plugin:0.8.10:report

Résultats attendus
------------------
- Un résumé 'TOTAL' lisible dans la sortie console pytest (présent dans la sortie --cov=term).
- Fichiers générés par service : `coverage.xml` et dossier `htmlcov/`.
- JaCoCo : rapport HTML dans `desktop-app/target/site/jacoco/index.html` (et `jacoco.xml` si configuré).

Remarque CI
-----------
Pour ce sprint (Sprint 1) nous ne bloquons pas la CI sur des seuils de couverture. La baseline est uniquement mesurée et documentée. Les verrous/seuils seront envisagés en Sprint 2.

---

<!-- fin de la section Baseline couverture (Sprint 1) -->
