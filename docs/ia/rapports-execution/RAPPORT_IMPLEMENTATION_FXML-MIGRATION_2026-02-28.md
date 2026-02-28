# RAPPORT_IMPLEMENTATION_FXML-MIGRATION_2026-02-28

> **Généré par IA** — Copilot (GitHub Copilot Agent)
> **Auteur responsable** : Équipe comic2pdf-app

---

## 1. Titre et type

**Type** : IMPLEMENTATION
**Sujet** : Migration de l'UI desktop JavaFX — code-only → FXML + Controllers

---

## 2. Date

2026-02-28

---

## 3. Contexte et résumé

L'application desktop `comic2pdf-app` disposait d'une interface JavaFX construite entièrement
en code Java (`MainView extends BorderPane`, `JobsView extends BorderPane`,
`config/ConfigView extends VBox`). Ce rapport documente la migration complète vers une
architecture **FXML + Controllers** avec injection manuelle des services via `AppServices`
(container DI sans ServiceLocator), conformément à la spec d'architecture MVC JavaFX.
Les IDs FXML (`#mainTabs`, `#tabDuplicates`, `#tabJobs`, `#tabConfig`, etc.) ont été
conservés identiques pour préserver les 4 tests UI TestFX existants sans modification.

---

## 4. Description des changements

### Fichiers créés

| Fichier | Type | Description |
|---|---|---|
| `desktop-app/src/main/java/.../service/AppServices.java` | Nouveau | Container de services (OrchestratorClient + DuplicateService + ConfigService). Méthode `createDefault()` lit ORCHESTRATOR_URL depuis env. |
| `desktop-app/src/main/java/.../util/FxUtils.java` | Nouveau | Helpers UI statiques : `openDirectory(Path)`, `showError()`, `showInfo()` |
| `desktop-app/src/main/java/.../ui/controller/MainController.java` | Nouveau | Controller principal FXML : injection des services vers les 3 sous-controllers via `<fx:include>` |
| `desktop-app/src/main/java/.../ui/controller/DuplicatesController.java` | Nouveau | Controller onglet Doublons : `@FXML`, `setServices()`, `onRefreshDuplicates()`, dépôt atomique `.part` |
| `desktop-app/src/main/java/.../ui/controller/JobsController.java` | Nouveau | Controller onglet Jobs : `ScheduledService` poll 3s, `setAutoRefresh(boolean)` pour tests |
| `desktop-app/src/main/java/.../ui/controller/ConfigController.java` | Nouveau | Controller onglet Configuration : `SpinnerValueFactory`, `onApplyConfig()`, `loadConfig()` |
| `desktop-app/src/main/resources/fxml/MainView.fxml` | Nouveau | TabPane 3 onglets + `<fx:include>` (IDs stables) |
| `desktop-app/src/main/resources/fxml/DuplicatesView.fxml` | Nouveau | Vue doublons FXML |
| `desktop-app/src/main/resources/fxml/JobsView.fxml` | Nouveau | Vue jobs FXML |
| `desktop-app/src/main/resources/fxml/ConfigView.fxml` | Nouveau | Vue configuration FXML |

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `desktop-app/src/main/java/.../MainApp.java` | Modifié | Bootstrap FXML via FXMLLoader + injection AppServices dans MainController via setter |
| `desktop-app/src/test/java/.../ui/TestableMainApp.java` | Modifié | Même bootstrap FXML que production + injection des overrides de test via setters des controllers |
| `desktop-app/src/test/java/.../ui/ConfigUiTest.java` | Modifié | `start(Stage) throws Exception` (propagation signature) |
| `desktop-app/src/test/java/.../ui/MainAppUiTest.java` | Modifié | idem |
| `desktop-app/src/test/java/.../ui/DuplicatesUiTest.java` | Modifié | idem |
| `desktop-app/src/test/java/.../ui/JobsUiTest.java` | Modifié | idem |

### Fichiers supprimés

| Fichier | Raison |
|---|---|
| `desktop-app/src/main/java/.../MainView.java` | Remplacé par `DuplicatesView.fxml` + `DuplicatesController` |
| `desktop-app/src/main/java/.../JobsView.java` | Remplacé par `JobsView.fxml` + `JobsController` |
| `desktop-app/src/main/java/.../config/ConfigView.java` | Remplacé par `ConfigView.fxml` + `ConfigController` |

---

## 5. Architecture finale

```
MainApp.java (bootstrap)
  └── FXMLLoader → MainView.fxml (TabPane)
        ├── fx:include → DuplicatesView.fxml → DuplicatesController
        │     └── DuplicateService (DI via AppServices)
        ├── fx:include → JobsView.fxml → JobsController
        │     └── OrchestratorClient (DI via AppServices)
        └── fx:include → ConfigView.fxml → ConfigController
              └── ConfigService + OrchestratorClient (DI via AppServices)

AppServices.createDefault()
  ├── OrchestratorClient(ORCHESTRATOR_URL env)
  ├── DuplicateService()
  └── ConfigService()
```

---

## 6. IDs FXML stables (compatibles tests UI existants)

| ID | Fichier FXML | Testé par |
|---|---|---|
| `#mainTabs` | `MainView.fxml` | `MainAppUiTest` |
| `#tabDuplicates` | `MainView.fxml` | `MainAppUiTest` |
| `#tabJobs` | `MainView.fxml` | `MainAppUiTest` |
| `#tabConfig` | `MainView.fxml` | `MainAppUiTest` |
| `#duplicatesTable` | `DuplicatesView.fxml` | `DuplicatesUiTest` |
| `#duplicatesRefreshBtn` | `DuplicatesView.fxml` | `DuplicatesUiTest` |
| `#jobsRefreshBtn` | `JobsView.fxml` | `JobsUiTest` |
| `#jobsTable` | `JobsView.fxml` | `JobsUiTest` |
| `#applyConfigBtn` | `ConfigView.fxml` | `ConfigUiTest` |

---

## 7. Étapes pour reproduire / commandes exécutées

```powershell
# Tests unitaires (sans UI)
cd desktop-app
mvn test
# Résultat : Tests run: 21, Failures: 0, Errors: 0

# Tests UI (@Tag("ui"))
mvn -Pui-tests test
# Résultat : Tests run: 4, Failures: 0, Errors: 0

# Lancer l'application
mvn javafx:run
# OU via script
.\scripts\run_desktop.ps1

# Tests UI headless (opt-in)
mvn -Pui-tests test -Dtestfx.headless=true -Dprism.order=sw
```

---

## 8. Fichiers modifiés — chemins pertinents

- `desktop-app/src/main/java/com/comic2pdf/desktop/MainApp.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/service/AppServices.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/util/FxUtils.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/ui/controller/` (4 fichiers)
- `desktop-app/src/main/resources/fxml/` (4 fichiers FXML)
- `desktop-app/src/test/java/com/comic2pdf/desktop/ui/TestableMainApp.java`
- `desktop-app/src/test/java/com/comic2pdf/desktop/ui/*.java` (4 fichiers — signature)

---

## 9. Liens vers PR / issues

N/A — travail local, aucune PR GitHub ouverte.

---

## 10. Contact pour questions

Pour des questions sur cette migration, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

