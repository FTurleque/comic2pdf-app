# RAPPORT_IMPLEMENTATION_UI-TESTS-LANCEMENT_2026-02-28

> **Généré par IA** — Outil/Agent : `GitHub Copilot (mode Agent)`
> **Auteur responsable** : `équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | `Tests UI TestFX + scripts de lancement desktop` |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-02-28` |
| **Auteur(s)** | `équipe comic2pdf-app` |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | `—` |

---

## 2. Contexte et résumé

L'application desktop JavaFX (`desktop-app`) existait et compilait mais n'avait ni IDs stables
pour les composants UI, ni tests TestFX, ni scripts de lancement reproductibles.
Ce rapport documente l'ajout du profil Maven `ui-tests` (TestFX 4.0.18 + Monocle 21.0.2),
la création de `TestableMainApp` pour l'injection sans constructeur (contrainte reflection TestFX),
l'écriture de 4 tests UI avec stubs HTTP stdlib, et 10 scripts de lancement + mise à jour de la doc.

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `desktop-app/pom.xml` | Ajout `testfx-junit5` + `openjfx-monocle`, Surefire `excludedGroups=ui`, profil `ui-tests` avec `groups=ui` + `combine.self=override` + `argLine add-opens` |
| `desktop-app/src/main/java/.../MainApp.java` | Ajout `setId()` sur `tabPane`, `tabDuplicates`, `tabJobs`, `tabConfig` |
| `desktop-app/src/main/java/.../MainView.java` | Ajout `MainView(String initialDataDir)`, délégation no-arg, `setId()` sur `dataDirField`, `duplicatesTable`, `mainStatusLabel`, `duplicatesRefreshBtn` |
| `desktop-app/src/main/java/.../JobsView.java` | Ajout `JobsView(client, dataDirField, boolean autoRefresh)`, délégation, `setId()` sur `jobsTable`, `jobsStatusLabel`, `jobsRefreshBtn` |
| `desktop-app/src/main/java/.../config/ConfigView.java` | Ajout `setId()` sur `orchestratorUrlField`, `applyConfigBtn`, `configStatusLabel` |
| `docs/dev/testing.md` | Ajout section "Tests UI JavaFX (TestFX)" |
| `docs/dev/setup.md` | Ajout section "Lancer l'application desktop JavaFX" |

### Fichiers créés

| Fichier | Description |
|---|---|
| `desktop-app/src/test/java/.../ui/TestableMainApp.java` | Application TestFX injectable via `Optional` statiques |
| `desktop-app/src/test/java/.../ui/MainAppUiTest.java` | Vérifie présence des 3 onglets |
| `desktop-app/src/test/java/.../ui/DuplicatesUiTest.java` | Refresh doublons depuis rapport JSON |
| `desktop-app/src/test/java/.../ui/JobsUiTest.java` | Refresh jobs depuis stub `GET /jobs` |
| `desktop-app/src/test/java/.../ui/ConfigUiTest.java` | Apply config → stub `POST /config` |
| `scripts/dev_up.ps1` + `.sh` | `docker compose up -d --build` |
| `scripts/dev_down.ps1` + `.sh` | `docker compose down` |
| `scripts/run_desktop.ps1` + `.sh` | Lance l'UI avec `ORCHESTRATOR_URL=http://localhost:18083` |
| `scripts/run_ui_tests.ps1` + `.sh` | `mvn -Pui-tests test` |
| `scripts/run_ui_tests_headless.ps1` + `.sh` | `mvn -Pui-tests test -Dtestfx.headless=true ...` |

---

## 4. Étapes pour reproduire / commandes exécutées

### Tests unitaires (sans UI)

```powershell
cd desktop-app
mvn test
# Résultat : Tests run: 21, Failures: 0, Errors: 0, Skipped: 0 — BUILD SUCCESS
# Tests @Tag("ui") exclus automatiquement (excludedGroups=ui dans Surefire)
```

### Tests UI TestFX (mode visuel)

```powershell
cd desktop-app
mvn -Pui-tests test
# ou :
.\scripts\run_ui_tests.ps1
# Résultat : Tests run: 4, Failures: 0, Errors: 0 — BUILD SUCCESS
```

### Tests UI TestFX (mode headless Monocle)

```powershell
cd desktop-app
mvn -Pui-tests test -Dtestfx.headless=true -Dprism.order=sw -Dprism.verbose=true
# Si pas d'affichage : ajouter -Dglass.platform=Monocle -Dmonocle.platform=Headless
# ou :
.\scripts\run_ui_tests_headless.ps1
```

### Lancer l'UI desktop

```powershell
# Démarrer Docker d'abord
.\scripts\dev_up.ps1

# Lancer l'UI (variable d'environnement obligatoire, pas -D)
.\scripts\run_desktop.ps1
# équivalent :
$env:ORCHESTRATOR_URL = "http://localhost:18083"
cd desktop-app
mvn -q javafx:run
```

---

## 5. Fichiers modifiés / chemins pertinents

- `desktop-app/pom.xml`
- `desktop-app/src/main/java/com/comic2pdf/desktop/MainApp.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/MainView.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/JobsView.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/config/ConfigView.java`
- `desktop-app/src/test/java/com/comic2pdf/desktop/ui/` (5 fichiers)
- `scripts/` (10 fichiers)
- `docs/dev/testing.md`
- `docs/dev/setup.md`

---

## 6. Liens et références

- Instructions Copilot : `.github/copilot-instructions.md`
- Instructions desktop : `.github/instructions/desktop-app.instructions.md`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Template rapport : `docs/ia/templates/rapport_template.md`
- Rapport d'implémentation initial : [`RAPPORT_IMPLEMENTATION_2026-02-28.md`](RAPPORT_IMPLEMENTATION_2026-02-28.md)

---

## 7. Limitations connues

| Limitation | Détail |
|---|---|
| **Mode headless** | Dépend de Monocle + JVM + OS. Sur certaines machines sans GPU, ajouter `-Dglass.platform=Monocle -Dmonocle.platform=Headless`. Non activé par défaut. |
| **`com.sun.net.httpserver`** | API interne Java stable depuis Java 6 mais non garantie. Si `InaccessibleObjectException` sur Java 21+, ajouter `--add-exports jdk.httpserver/com.sun.net.httpserver=ALL-UNNAMED` dans `argLine` du profil `ui-tests`. |
| **Séquentialité** | Les tests UI utilisent des `Optional` statiques dans `TestableMainApp`. Ils doivent rester séquentiels (comportement par défaut Surefire). Ne pas ajouter `@Execution(CONCURRENT)`. |
| **`@BeforeAll` statique** | TestFX JUnit 5 appelle `start()` avant `@BeforeEach`. Les overrides doivent être initialisés dans `@BeforeAll` (statique). Les tests utilisent donc `@BeforeAll` + `@AfterAll` plutôt que `@BeforeEach` + `@AfterEach`. |
| **ConfigService en test** | Le ConfigService enregistre la config sur le disque local (`AppData`) pendant les tests UI. Ce n'est pas un effet de bord bloquant mais peut modifier la config locale du développeur. |

---

## 8. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

