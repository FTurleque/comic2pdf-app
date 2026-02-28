---
description: Règles de code, tests et architecture pour l'application desktop JavaFX
applyTo: desktop-app/**
---

# Instructions — desktop-app

## Rôle
Interface JavaFX permettant :
1. De déposer des fichiers CBZ/CBR dans `data/in/` (convention `.part` → `.cbz/.cbr`).
2. D'afficher les doublons détectés par l'orchestrateur et d'écrire une décision.

## Structure des fichiers

```
desktop-app/
├── src/
│   ├── main/java/com/fturleque/comic2pdf/desktop/
│   │   ├── MainApp.java                       # Entrée JavaFX (extends Application)
│   │   ├── MainView.java                      # Vue principale (BorderPane) — UI uniquement
│   │   ├── DupRow.java                        # Modèle tableau (StringProperty JavaFX)
│   │   └── duplicates/
│   │       ├── DuplicateDecision.java         # Enum : USE_EXISTING_RESULT, DISCARD, FORCE_REPROCESS
│   │       └── DuplicateService.java          # Service pur : listDuplicates, writeDecision
│   └── test/java/com/fturleque/comic2pdf/desktop/
│       └── duplicates/
│           └── DuplicateServiceTest.java      # Tests JUnit 5 uniquement
└── pom.xml
```

## Architecture MVC — règle fondamentale

```
MainView (UI)  ──délègue──→  DuplicateService (logique pur)
                                    ↕ filesystem
                           data/reports/duplicates/*.json   (lecture)
                           data/hold/duplicates/<jk>/decision.json  (écriture)
```

**`MainView` ne contient aucune logique filesystem ni parsing JSON.**
Toute logique est dans `DuplicateService` (testable sans JavaFX).

## DuplicateService — contrat public

```java
// Lecture de tous les rapports doublons
List<DupRow> listDuplicates(Path dataDir) throws IOException;

// Écriture de la décision utilisateur
Path writeDecision(Path dataDir, String jobKey, DuplicateDecision decision) throws IOException;
```

### `listDuplicates(Path dataDir)`
- Lit `<dataDir>/reports/duplicates/*.json`.
- Crée le dossier si absent (`Files.createDirectories`).
- Ignore silencieusement les rapports corrompus (try/catch par fichier).
- Retourne une `List<DupRow>` (jamais `null`, peut être vide).

### `writeDecision(Path dataDir, String jobKey, DuplicateDecision decision)`
- Écrit dans `<dataDir>/hold/duplicates/<jobKey>/decision.json`.
- Crée les dossiers intermédiaires si absents.
- Payload JSON :
  ```json
  { "action": "DISCARD" }
  { "action": "USE_EXISTING_RESULT" }
  { "action": "FORCE_REPROCESS", "nonce": "<UUID>" }
  ```
- Ajoute `"nonce"` **uniquement** pour `FORCE_REPROCESS`.
- Retourne le `Path` du fichier écrit.

## DuplicateDecision — enum

```java
public enum DuplicateDecision {
    USE_EXISTING_RESULT,
    DISCARD,
    FORCE_REPROCESS
}
```

## DupRow — modèle JavaFX

Doit exposer :
- `getJobKey()` / `jobKeyProperty() : StringProperty`
- `getIncomingFile()` / `incomingFileProperty() : StringProperty`
- `getExistingState()` / `existingStateProperty() : StringProperty`

Ces getters sont utilisés par les `TableColumn.setCellValueFactory(...)` dans `MainView`.

## Format des fichiers (reference)

### `reports/duplicates/<jobKey>.json` (lecture)
```json
{
  "jobKey": "<fileHash>__<profileHash>",
  "detectedAt": "2026-01-01T00:00:00Z",
  "incoming": {
    "fileName": "mon_comic.cbz",
    "path": "/data/hold/duplicates/.../mon_comic.cbz",
    "sizeBytes": 12345
  },
  "existing": { "state": "DONE", "outPdf": "/data/out/..." },
  "profile": { "ocr": {...}, "prep": {...} },
  "actions": ["USE_EXISTING_RESULT", "DISCARD", "FORCE_REPROCESS"]
}
```

Champs lus par `DuplicateService.listDuplicates` :
- `node.path("jobKey").asText("")`
- `node.path("incoming").path("fileName").asText("")`
- `node.path("existing").path("state").asText("")`

### `hold/duplicates/<jobKey>/decision.json` (écriture)
```json
{ "action": "DISCARD" }
```

## Dépôt de fichier (MainView.depositFile)

Convention obligatoire `.part` → rename atomique :
```java
Files.copy(f.toPath(), part, StandardCopyOption.REPLACE_EXISTING);
Files.move(part, fin, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
```
Ne jamais copier directement vers le fichier final (l'orchestrateur détecterait un fichier incomplet).

## Configuration Maven (`pom.xml`)

| Dépendance | Version | Scope |
|---|---|---|
| `org.openjfx:javafx-controls` | 21.0.4 | compile |
| `org.openjfx:javafx-fxml` | 21.0.4 | compile |
| `com.fasterxml.jackson.core:jackson-databind` | 2.17.2 | compile |
| `org.junit.jupiter:junit-jupiter` | 5.10.3 | test |
| `maven-surefire-plugin` | 3.3.1 | build |
| `maven.compiler.release` | 21 | — |

## Tests JUnit 5

### Exigences absolues
- **Zéro test UI** — pas de `Application.launch`, `Platform.runLater` ni `FXRobot`.
- Utiliser `@TempDir Path dataDir` pour l'isolation complète du filesystem.
- Tester uniquement `DuplicateService`.

### Cas minimaux à couvrir (`DuplicateServiceTest.java`)

```
listDuplicates : rapport JSON minimal → 1 DupRow (jobKey, incomingFile, existingState corrects)
listDuplicates : dossier vide → liste vide (non null)
listDuplicates : rapport corrompu → ignoré, les autres lus (pas de crash)
listDuplicates : crée reports/duplicates/ si absent (assertDoesNotThrow)
writeDecision  : fichier écrit au bon chemin (hold/duplicates/<jk>/decision.json)
writeDecision  : crée les dossiers intermédiaires manquants
writeDecision FORCE_REPROCESS : "nonce" présent dans le JSON
writeDecision DISCARD : "nonce" absent du JSON
writeDecision USE_EXISTING_RESULT : action correcte dans le JSON
```

### Lancer les tests
```powershell
cd desktop-app
mvn test
```

## Anti-patterns

- ❌ Logique filesystem dans `MainView` — toujours dans un service pur.
- ❌ Tests UI JavaFX — utiliser `@TempDir` + JUnit 5 sur les services.
- ❌ Chemins hardcodés — utiliser `dataDirField.getText()` / `Paths.get(...)`.
- ❌ `mapper.readTree()` dans `MainView` — déléguer à `DuplicateService`.
- ❌ Copie directe sans `.part` pour le dépôt de fichier.
- ❌ Supprimer des fichiers dans `reports/duplicates/` depuis l'app desktop
  (l'orchestrateur s'en charge après avoir traité `decision.json`).

