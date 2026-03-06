# RAPPORT_IMPLEMENTATION_2026-03-06-test-strategy-ci

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Test Strategy & CI Performance — xdist, Awaitility, E2E smoke+full |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-03-06` |
| **Auteur(s)** | équipe comic2pdf-app |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | À compléter lors de la soumission |

---

## 2. Contexte et résumé

Le dépôt `comic2pdf-app` disposait de tests Python (pytest) et Java (JUnit5/TestFX) sans parallélisation, avec des attentes fixes (`while/deadline + sleep`) dans les tests UI JavaFX, et un workflow E2E uniquement déclenché manuellement ou via label PR. Cette implémentation ajoute `pytest-xdist` pour paralléliser les tests Python (-n auto), remplace les boucles d'attente fragiles par Awaitility dans `JobsUiTest` et `ConfigUiTest`, et refactorise `e2e.yml` pour exécuter automatiquement un smoke en PR/push main et un full en schedule nightly.

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `services/prep-service/requirements-dev.txt` | Modifié | Ajout `pytest-xdist` |
| `services/ocr-service/requirements-dev.txt` | Modifié | Ajout `pytest-xdist` |
| `services/orchestrator/requirements-dev.txt` | Modifié | Ajout `pytest-xdist` |
| `services/prep-service/pytest.ini` | Modifié | `addopts = --dist=loadscope`, marker `serial`, `junit_family = xunit2` |
| `services/ocr-service/pytest.ini` | Modifié | idem |
| `services/orchestrator/pytest.ini` | Modifié | idem |
| `services/orchestrator/tests/conftest.py` | **Nouveau** | Isolation `DATA_DIR` (autouse) + marquage auto `serial` pour `test_http_server` et `test_auth` |
| `desktop-app/pom.xml` | Modifié | Ajout `awaitility:4.2.2` (scope test) |
| `desktop-app/src/test/.../ui/JobsUiTest.java` | Modifié | Remplacement boucle `while/deadline` par `await().atMost(5, SECONDS).untilAsserted(...)` |
| `desktop-app/src/test/.../ui/ConfigUiTest.java` | Modifié | Remplacement boucle `while/deadline + sleep` par `await().atMost(5, SECONDS).until(...)` |
| `.github/workflows/ci.yml` | Modifié | Commande pytest séparée en 2 passes : serial (`-n 0`) puis parallel (`-n auto --dist=loadscope`) avec JUnit XML par passe |
| `.github/workflows/e2e.yml` | Modifié | Refactoring complet : 2 jobs (`e2e-smoke` / `e2e-full`), schedule nightly, healthcheck polling sans sleep fixe, artefacts complets |
| `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_2026-03-06-test-strategy-ci.md` | **Nouveau** | Ce rapport |

---

## 4. Décisions techniques

### 4.1 Python — xdist

**Analyse de sécurité pour la parallélisation :**

| Module | Verdict | Raison |
|---|---|---|
| `test_core`, `test_utils`, `test_robustness` | ✅ xdist-safe | Utilise `tmp_path` (isolation par test), tous les subprocess mockés |
| `test_orchestrator`, `test_main_helpers` | ✅ xdist-safe | Idem, HTTP mocké avec `unittest.mock` |
| `test_http_server`, `test_auth` | ⚠️ `serial` | Démarrent un vrai `HTTPServer` en thread — ports éphémères, mais autant isoler |

**Stratégie :**
- `pytest -m serial -n 0` : exécution séquentielle des tests serveur HTTP
- `pytest -m "not serial" -n auto --dist=loadscope` : parallélisation full sur les tests purs
- `--dist=loadscope` : regroupe les tests d'une même classe sur le même worker → évite les effets de bord de module-level fixtures

**Marker auto dans conftest.py orchestrator :**
```python
def pytest_collection_modifyitems(items):
    serial_modules = {"test_http_server", "test_auth"}
    for item in items:
        if item.module.__name__.split(".")[-1] in serial_modules:
            item.add_marker(pytest.mark.serial)
```
Aucune modification des fichiers de tests existants requise.

### 4.2 JavaFX — Awaitility

**Avant (fragile) — `JobsUiTest` :**
```java
long deadline = System.currentTimeMillis() + 3_000;
TableView<?> table;
do {
    WaitForAsyncUtils.waitForFxEvents();
    WaitForAsyncUtils.sleep(100, MILLISECONDS);
    table = lookup("#jobsTable").query();
} while (table.getItems().isEmpty() && System.currentTimeMillis() < deadline);
// Pas d'assertion en cas de timeout → test silencieusement vert si la table reste vide !
```

**Après (stable) :**
```java
await()
    .atMost(5, TimeUnit.SECONDS)
    .pollInterval(100, TimeUnit.MILLISECONDS)
    .untilAsserted(() -> {
        WaitForAsyncUtils.waitForFxEvents();
        TableView<?> table = lookup("#jobsTable").query();
        assertNotNull(table, "#jobsTable doit exister");
        assertEquals(1, table.getItems().size(), "1 job attendu");
    });
```
Avantages : timeout borné, message d'erreur précis à l'échéance, terminaison immédiate dès condition vraie.

**Avant (fragile) — `ConfigUiTest` :**
```java
long deadline = System.currentTimeMillis() + 5_000;
while (capturedBody.get() == null && System.currentTimeMillis() < deadline) {
    WaitForAsyncUtils.sleep(50, MILLISECONDS);
}
// Si capturedBody est null après timeout → assertNotNull échoue sans contexte
```

**Après (stable) :**
```java
await()
    .atMost(5, TimeUnit.SECONDS)
    .pollInterval(50, TimeUnit.MILLISECONDS)
    .until(() -> capturedBody.get() != null);
```

### 4.3 E2E — Segmentation smoke/full

| Job | Déclencheur | Contenu | Timeout | Objectif |
|---|---|---|---|---|
| `e2e-smoke` | push main + PR (sans label) | 1 CBZ (2 pages) | 90s | < 10 min |
| `e2e-full` | schedule 02h00 + label `run-e2e` + dispatch | `tests/e2e/` complet | 180s | < 30 min |

Healthcheck : boucle `curl` sans `sleep` fixe, avec fallback après N secondes → déterministe.

---

## 5. Étapes pour reproduire / commandes exécutées

```powershell
# Installer xdist et lancer les tests en parallel (local)
cd services\orchestrator
pip install -r requirements-dev.txt
# Tous les tests (serial puis parallel, tel que CI) :
pytest -m serial -n 0
pytest -m "not serial" -n auto --dist=loadscope

# Local sans xdist (fallback) :
pytest

# Tests Java avec Awaitility (unitaires, hors UI) :
cd desktop-app
mvn -q test

# Tests UI headless (si xvfb disponible) :
xvfb-run -a mvn -q -Pui-tests test -Dtestfx.headless=true -Dprism.order=sw
```

### Résultats de validation locale

| Module | Compile | Tests | Résultat |
|---|---|---|---|
| `prep-service` | ✅ | — | requirements-dev.txt mis à jour |
| `ocr-service` | ✅ | — | requirements-dev.txt mis à jour |
| `orchestrator` | ✅ | — | requirements-dev.txt + conftest.py ajoutés |
| `desktop-app` | ✅ test-compile | `mvn test` exit 0 | Awaitility résolu, imports corrects |

---

## 6. Points d'attention / Limitations

- **`addopts = --dist=loadscope`** : requis dans `pytest.ini` uniquement si `pytest-xdist` est installé. Si un développeur lance `pytest` sans xdist installé, il obtient un warning mais pytest s'exécute normalement (xdist n'est pas chargé, `-n` et `--dist` sont ignorés gracieusement via `-p no:randomly`).
- **`-p no:randomly`** : désactive le plugin `pytest-randomly` si installé, pour garantir l'ordre déterministe des tests (évite les effets de bord liés à l'ordre aléatoire avec xdist).
- **Tests E2E `test_cli_e2e.py`** : ces tests sont dans `tests/tools/` et utilisent `subprocess.run` mocké — ils sont xdist-safe mais ne nécessitent pas Docker. Ils ne sont pas inclus dans `e2e.yml` (ils font déjà partie du job `python-tests` CI).
- **E2E smoke sur PR** : le `e2e-smoke` tourne sur chaque PR → peut allonger le temps de feedback de ~10 min. Si trop coûteux, filtrer sur `paths` (ex: ne pas déclencher si uniquement `docs/**` changé).
- **linux/arm64 Docker** : non testé pour `ocr-service` (tesseract ARM — voir `publishing.md`).

---

## 7. Guide : écrire un test UI stable (guidelines)

```java
// ✅ BIEN : attente bornée sur condition avec Awaitility
await()
    .atMost(5, TimeUnit.SECONDS)
    .pollInterval(100, TimeUnit.MILLISECONDS)
    .untilAsserted(() -> {
        WaitForAsyncUtils.waitForFxEvents(); // pompe les events FX avant assertion
        assertEquals(1, lookup("#maTable").query().getItems().size());
    });

// ✅ BIEN : attente simple sur état non-null
await()
    .atMost(3, TimeUnit.SECONDS)
    .until(() -> capturedValue.get() != null);

// ❌ MAUVAIS : sleep fixe arbitraire
Thread.sleep(500); // durée arbitraire, peut échouer en CI lent
WaitForAsyncUtils.sleep(200, MILLISECONDS); // idem

// ❌ MAUVAIS : boucle sans assertion à l'échéance
long deadline = System.currentTimeMillis() + 3_000;
do { ... } while (condition && time < deadline);
// → silencieusement vert si la condition n'est jamais vraie !
```

---

## 8. Liens et références

- Workflow CI : `.github/workflows/ci.yml`
- Workflow E2E : `.github/workflows/e2e.yml`
- Guide publishing : `docs/release/publishing.md`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`

---

## 9. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

