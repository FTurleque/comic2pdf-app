# Tests — comic2pdf-app

Ce guide détaille la stratégie de test, les commandes à exécuter et la façon d'ajouter de nouveaux tests.

---

## Vue d'ensemble des tests

| Module | Framework | Fichiers de test | Nombre de tests |
|---|---|---|---|
| `prep-service` | pytest | `test_core.py` | 12 |
| `ocr-service` | pytest | `test_core.py`, `test_jobs.py` | 17 |
| `orchestrator` | pytest | `test_core.py`, `test_orchestrator.py`, `test_robustness.py`, `test_http_server.py`, `test_logger.py` | 68 |
| `desktop-app` | JUnit 5 | `ConfigServiceTest.java`, `DuplicateServiceTest.java`, `OrchestratorClientTest.java` | 21 |

---

## Tests Python (pytest)

### prep-service

```powershell
# Windows PowerShell
cd services\prep-service
.\.venv\Scripts\Activate.ps1  # ou activer le venv si déjà créé
pytest -q
```

```bash
# Linux / macOS
cd services/prep-service
source .venv/bin/activate
pytest -q
```

**Résultat attendu** : `12 passed` (ou similar)

### ocr-service

```powershell
# Windows PowerShell
cd services\ocr-service
.\.venv\Scripts\Activate.ps1
pytest -q
```

```bash
# Linux / macOS
cd services/ocr-service
source .venv/bin/activate
pytest -q
```

**Résultat attendu** : `17 passed`

### orchestrator

```powershell
# Windows PowerShell
cd services\orchestrator
.\.venv\Scripts\Activate.ps1
pytest -q
```

```bash
# Linux / macOS
cd services/orchestrator
source .venv/bin/activate
pytest -q
```

**Résultat attendu** : `68 passed`

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

**Résultat attendu** : `BUILD SUCCESS` — `Tests run: 21, Failures: 0, Errors: 0`

> Aucune instance JavaFX n'est démarrée pendant ces tests. Ils portent uniquement sur la logique de service (filesystem, HTTP parsing).

---

## Tests UI JavaFX (TestFX — profil `ui-tests`)

Les tests UI sont tagués `@Tag("ui")` et **exclus de `mvn test`** par défaut.
Pour les exécuter, utiliser le profil Maven `ui-tests`.

### Mode visuel par défaut (requiert un écran)

```powershell
# Windows PowerShell
cd desktop-app
mvn -Pui-tests test

# ou via le script
.\scripts\run_ui_tests.ps1
```

```bash
# Linux / macOS
cd desktop-app
mvn -Pui-tests test

# ou via le script
./scripts/run_ui_tests.sh
```

**Résultat attendu** : `BUILD SUCCESS` — `Tests run: 4, Failures: 0, Errors: 0`

### Mode headless Monocle (opt-in, sans écran)

```powershell
# Windows PowerShell
cd desktop-app
mvn -Pui-tests test -Dtestfx.headless=true -Dprism.order=sw -Dprism.verbose=true

# ou via le script
.\scripts\run_ui_tests_headless.ps1
```

```bash
# Linux / macOS
./scripts/run_ui_tests_headless.sh
```

> Si aucune fenêtre ne s'affiche (serveur sans GPU), ajouter :
> `-Dglass.platform=Monocle -Dmonocle.platform=Headless`

> **Note `InaccessibleObjectException`** (rare sur Java 21+) : si Surefire lève une erreur
> sur `com.sun.net.httpserver`, ajouter dans `argLine` du profil `ui-tests` dans `pom.xml` :
> `--add-exports jdk.httpserver/com.sun.net.httpserver=ALL-UNNAMED`

### Séquentialité des tests UI

Les tests UI utilisent `TestableMainApp` avec des champs statiques (`Optional`).
Les tests s'exécutent **séquentiellement** (comportement par défaut Surefire).
Ne pas ajouter `@Execution(CONCURRENT)` sur les classes de tests UI.

### Tests UI disponibles

| Classe | Ce qu'elle couvre |
|---|---|
| `MainAppUiTest` | Les 3 onglets (Doublons, Jobs, Configuration) sont présents |
| `DuplicatesUiTest` | Refresh doublons → table remplie depuis un JSON de rapport |
| `ConfigUiTest` | Apply config → stub HTTP local reçoit le JSON attendu |
| `JobsUiTest` | Refresh manuel jobs → table remplie depuis stub `GET /jobs` |

> Aucun test UI ne se connecte au backend réel. Tous utilisent des stubs `com.sun.net.httpserver.HttpServer`.

---

## Script global `run_tests.ps1`

Lance tous les tests Python et Java en une seule commande depuis la racine :

```powershell
# Windows PowerShell (depuis la racine du dépôt)
.\run_tests.ps1
```

Le script :
1. Installe les dépendances dev de chaque service Python (`pip install -r requirements-dev.txt`)
2. Lance `pytest -q` dans chaque service Python
3. Lance `mvn -q test` dans `desktop-app`
4. Affiche un résumé coloré `PASS` / `FAIL` par module
5. Retourne `exit 1` si au moins un module échoue

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

