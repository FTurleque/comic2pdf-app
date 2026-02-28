---
description: Ajouter une nouvelle vue ou fonctionnalité à l'application desktop JavaFX
---

# Prompt — update-desktop-ui

## Goal
Ajouter `<description de la fonctionnalité>` dans l'application desktop `comic2pdf-app`,
en respectant la séparation `DuplicateService` (logique) / `MainView` (UI).

## Context

Architecture desktop :
```
MainView (BorderPane)
  ├── buildConfigRow()   → champ DATA_DIR, boutons refresh/open
  ├── buildActionsRow()  → bouton dépôt fichier
  ├── buildTable()       → TableView<DupRow> avec colonne Actions
  └── buildBottom()      → statusLabel

DuplicateService (service pur)
  ├── listDuplicates(Path dataDir) → List<DupRow>
  └── writeDecision(Path dataDir, String jobKey, DuplicateDecision) → Path
```

Fichiers concernés :
- `desktop-app/src/main/java/com/comic2pdf/desktop/MainView.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/duplicates/DuplicateService.java`
- `desktop-app/src/main/java/com/comic2pdf/desktop/DupRow.java`
- `desktop-app/src/test/java/com/comic2pdf/desktop/duplicates/DuplicateServiceTest.java`

## Task
`<Description précise de ce qui doit être ajouté ou modifié.>`

## Steps

### 1. Lire les fichiers existants
```
read_file desktop-app/src/main/java/.../MainView.java
read_file desktop-app/src/main/java/.../duplicates/DuplicateService.java
read_file desktop-app/src/main/java/.../DupRow.java
read_file desktop-app/src/test/java/.../duplicates/DuplicateServiceTest.java
```

### 2. Identifier la logique métier impliquée
- Quels fichiers sont lus ou écrits ?
- Quel est le format JSON ?
- S'agit-il d'une lecture de `reports/duplicates/`, d'une écriture dans `hold/duplicates/`,
  ou d'autre chose ?

### 3. Étendre le service pur (avant de toucher l'UI)

**Cas A : extension de `DuplicateService`**
```java
// Ajouter dans DuplicateService.java
/**
 * <Javadoc FR>
 *
 * @param dataDir Racine data/.
 * @param <param> Description.
 * @return Description.
 * @throws IOException En cas d'erreur d'accès au filesystem.
 */
public <ReturnType> <nomMethode>(Path dataDir, ...) throws IOException {
    // Logique pure : filesystem + Jackson uniquement, zéro JavaFX
}
```

**Cas B : nouveau service pur (scope différent)**
```java
package com.comic2pdf.desktop.<package>;

public class <NomService> {
    private final ObjectMapper mapper;
    public <NomService>() { this.mapper = new ObjectMapper(); }
    public <NomService>(ObjectMapper mapper) { this.mapper = mapper; }

    public <ReturnType> <nomMethode>(Path dataDir, ...) throws IOException { ... }
}
```

### 4. Écrire les tests JUnit 5 AVANT d'implémenter l'UI

```java
@Test
@DisplayName("<nom>-service : <description>")
void <nomTest>(@TempDir Path dataDir) throws IOException {
    // 1. Préparer les fichiers JSON dans dataDir
    Path dir = dataDir.resolve("...").resolve("...");
    Files.createDirectories(dir);
    Files.writeString(dir.resolve("test.json"), """
        { "champ": "valeur" }
        """);

    // 2. Appeler le service
    var service = new DuplicateService();
    var result = service.<nomMethode>(dataDir, ...);

    // 3. Vérifier
    assertEquals("valeur", result.get<Champ>());
    assertTrue(Files.exists(dataDir.resolve("...")));
}
```

Vérifier : `mvn test` vert avant de modifier `MainView`.

### 5. Étendre `DupRow` si nécessaire

```java
// Dans DupRow.java
private final StringProperty <nouveauChamp>;

public DupRow(String jobKey, String incomingFile, String existingState, String <nouveauChamp>) {
    // ...existing code...
    this.<nouveauChamp> = new SimpleStringProperty(<nouveauChamp>);
}

public String get<NouveauChamp>() { return <nouveauChamp>.get(); }
public StringProperty <nouveauChamp>Property() { return <nouveauChamp>; }
```

### 6. Brancher dans `MainView`

**Nouveau bouton :**
```java
// Dans buildActionsRow() ou buildConfigRow()
var btn = new Button("<Label>");
btn.setOnAction(e -> <nomMethodeUI>());
// Ajouter btn dans le HBox existant
```

**Nouvelle colonne dans le tableau :**
```java
// Dans buildTable()
var col<Nom> = new TableColumn<DupRow, String>("<NomColonne>");
col<Nom>.setCellValueFactory(c -> c.getValue().<nouveauChamp>Property());
dupTable.getColumns().add(col<Nom>);
```

**Méthode UI (délégation pure) :**
```java
private void <nomMethodeUI>() {
    try {
        var result = duplicateService.<nomMethode>(Paths.get(dataDirField.getText()));
        // Mettre à jour l'UI
        statusLabel.setText("... : " + result);
    } catch (IOException ex) {
        statusLabel.setText("Erreur : " + ex.getMessage());
    }
}
```

### 7. Valider

```powershell
cd desktop-app
mvn test          # Tests JUnit 5 verts (aucun test UI)
```

Si environnement graphique disponible :
```powershell
mvn javafx:run    # Application se lance sans erreur
```

## Constraints

- **Zéro logique filesystem dans `MainView`** — toujours dans le service pur.
- **Zéro test UI** — `@TempDir` + JUnit 5 sur les services uniquement.
- Ne pas ajouter de dépendance lourde (Spring, Hibernate, etc.).
- Toute nouvelle dépendance prod doit avoir une version fixée dans `pom.xml`.
- Si un nouveau type de décision est ajouté dans `DuplicateDecision`,
  **coordonner avec `services-maintainer`** pour que l'orchestrateur le gère dans
  `check_duplicate_decisions` (`services/orchestrator/app/main.py`).
- Javadoc en français pour toutes les méthodes publiques (`@param`, `@return`, `@throws`).

## Examples

### Ajouter un filtre "afficher seulement les DONE" dans la liste des doublons
1. Ajouter `listDuplicatesByState(Path dataDir, String state)` dans `DuplicateService`.
2. Test : rapport DONE + rapport QUEUED → retourne seulement DONE.
3. Ajouter un `ComboBox<String>` dans `buildConfigRow()`.
4. Handler du ComboBox → appel `listDuplicatesByState` → `dupTable.getItems().setAll(rows)`.

### Ajouter une colonne "taille du fichier entrant"
1. Ajouter `sizeBytes` dans `DupRow`.
2. Lire `node.path("incoming").path("sizeBytes").asLong(0)` dans `listDuplicates`.
3. Ajouter la `TableColumn` dans `buildTable()`.
4. Test : rapport avec `sizeBytes: 100` → `row.getSizeBytes() == "100"`.

