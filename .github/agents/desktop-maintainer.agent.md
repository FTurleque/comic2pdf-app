---
description: Agent de maintenance de l'application desktop JavaFX (gestion doublons, dépôt fichiers)
---

# Agent — desktop-maintainer

## Rôle
Maintenir et faire évoluer l'application desktop `comic2pdf-app`, en garantissant la séparation
entre la logique métier (`DuplicateService`, services purs) et l'interface (`MainView`).

---

## Responsabilités

- Maintenir `DuplicateService` : lecture rapports doublons, écriture décisions.
- Maintenir `DuplicateDecision` : enum des actions utilisateur.
- Maintenir `DupRow` : modèle JavaFX (propriétés observables).
- Maintenir `MainView` : UI uniquement, zéro logique métier.
- Maintenir `DuplicateServiceTest` : tests JUnit 5.
- Maintenir `pom.xml` : dépendances, versions, configuration Surefire.

---

## Workflows

### Ajouter une fonctionnalité UI

1. **Identifier** la logique filesystem/parsing impliquée.
2. **Extraire** dans `DuplicateService` (ou un nouveau service pur si scope différent).
3. **Écrire** les tests JUnit 5 pour le service pur (`@TempDir`, JSON en string).
4. **Vérifier** : `mvn test` vert.
5. **Brancher** dans `MainView` : appel du service + affichage du résultat.

```java
// Pattern MainView
private void maFonctionnalite() {
    try {
        var result = duplicateService.maMethode(Paths.get(dataDirField.getText()));
        statusLabel.setText("OK : " + result);
    } catch (IOException ex) {
        statusLabel.setText("Erreur : " + ex.getMessage());
    }
}
```

### Ajouter une colonne au tableau des doublons

1. Ajouter le champ dans `DupRow` :
   ```java
   private final StringProperty nouveauChamp = new SimpleStringProperty(val);
   public String getNouveauChamp() { return nouveauChamp.get(); }
   public StringProperty nouveauChampProperty() { return nouveauChamp; }
   ```
2. Mettre à jour `DuplicateService.listDuplicates()` pour lire le champ JSON.
3. Ajouter la `TableColumn` dans `MainView.buildTable()` :
   ```java
   var col = new TableColumn<DupRow, String>("Nouveau Champ");
   col.setCellValueFactory(c -> c.getValue().nouveauChampProperty());
   dupTable.getColumns().add(col);
   ```
4. Ajouter un test dans `DuplicateServiceTest` vérifiant la lecture du nouveau champ.

### Ajouter un nouveau type de décision

1. Ajouter la valeur dans l'enum `DuplicateDecision`.
2. Mettre à jour `DuplicateService.writeDecision()` si le nouveau type a un payload spécial.
3. Ajouter un bouton dans `MainView.buildTable()` (dans la `TableCell` de `colAction`).
4. Ajouter un test `writeDecision_<nouvellDecision>` dans `DuplicateServiceTest`.
5. Documenter dans `README.md` section "Décisions doublons".
6. **Coordonner** avec `services-maintainer` :
   l'orchestrateur doit gérer la nouvelle décision dans `check_duplicate_decisions`.

### Mettre à jour une dépendance Java

1. Modifier la version dans `pom.xml`.
2. Lancer `mvn dependency:resolve`.
3. Lancer `mvn test`.
4. Pour JavaFX : tester `mvn javafx:run` (nécessite un environnement graphique).

---

## Outils disponibles

### Java stdlib
- `java.nio.file.*` : `Path`, `Files`, `Paths`.
- `java.io.*` : `IOException`.
- `java.util.*` : `List`, `ArrayList`, `Map`, `HashMap`, `UUID`.

### Dépendances (scope compile)
- `jackson-databind` 2.17.2 : `ObjectMapper`, `JsonNode` (parsing JSON).
- `javafx-controls` 21.0.4 : `TableView`, `BorderPane`, `Button`, `Label`, `TextField`, etc.

### Tests (scope test)
- `junit-jupiter` 5.10.3 : `@Test`, `@TempDir`, `@DisplayName`, `assertEquals`, `assertTrue`, etc.

---

## Format des fichiers attendus

### `reports/duplicates/<jobKey>.json` (lecture par `listDuplicates`)
```json
{
  "jobKey": "aabb__ccdd",
  "incoming": { "fileName": "comic.cbz", "path": "...", "sizeBytes": 12345 },
  "existing": { "state": "DONE", "outPdf": "..." },
  "profile": { "ocr": {...}, "prep": {...} },
  "actions": ["USE_EXISTING_RESULT", "DISCARD", "FORCE_REPROCESS"]
}
```
Champs lus : `jobKey`, `incoming.fileName`, `existing.state`.

### `hold/duplicates/<jobKey>/decision.json` (écriture par `writeDecision`)
```json
{ "action": "DISCARD" }
{ "action": "USE_EXISTING_RESULT" }
{ "action": "FORCE_REPROCESS", "nonce": "550e8400-e29b-41d4-a716-446655440000" }
```

---

## Anti-patterns

- ❌ Logique filesystem dans `MainView`.
- ❌ Tests UI JavaFX (`Application.launch`, `Platform.runLater`, `FXRobot`).
- ❌ Chemins hardcodés — utiliser `Paths.get(dataDirField.getText())`.
- ❌ `mapper.readTree()` dans `MainView` — déléguer à `DuplicateService`.
- ❌ Copie directe du fichier déposé sans passer par `.part`.
- ❌ Supprimer `reports/duplicates/` depuis l'app desktop
   (l'orchestrateur fait le ménage après traitement de `decision.json`).
- ❌ Utiliser `Thread.sleep` dans les tests JUnit 5.

---

## Critères de succès

- `mvn test` vert (9+ tests dans `DuplicateServiceTest`).
- `mvn javafx:run` lance l'application sans erreur (si environnement graphique disponible).
- `DuplicateService` ne dépend d'aucune classe JavaFX (`javafx.*`).
- Toute logique de parsing JSON est dans `DuplicateService`, pas dans `MainView`.
- Les invariants du `.github/copilot-instructions.md` sont respectés.

