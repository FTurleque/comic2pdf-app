# Configurations IntelliJ IDEA (Run/Debug)

Ce dossier contient les configurations de lancement IntelliJ IDEA pour le projet `comic2pdf-app`.

## Configurations disponibles

### 1. Comic2PDF - Desktop Debug
- **Type** : Application Java
- **Classe principale** : `com.fturleque.comic2pdf.desktop.MainApp`
- **Module** : `desktop-app`
- **Variables d'environnement** : `ORCHESTRATOR_URL=http://localhost:18083`
- **Usage** : Lancement direct de l'application JavaFX avec support complet du debugger IntelliJ

### 2. Comic2PDF - Desktop Run (Maven)
- **Type** : Maven
- **Goal** : `javafx:run`
- **Working directory** : `$PROJECT_DIR$/desktop-app`
- **Variables d'environnement** : `ORCHESTRATOR_URL=http://localhost:18083`
- **Usage** : Lancement via le plugin Maven JavaFX (équivalent à `mvn javafx:run`)

### 3. Comic2PDF - Desktop UI Tests
- **Type** : Maven
- **Goal** : `test`
- **Profil** : `ui-tests`
- **Working directory** : `$PROJECT_DIR$/desktop-app`
- **Usage** : Exécution des tests UI avec TestFX (équivalent à `mvn -Pui-tests test`)

## Prérequis

1. **Stack Docker démarrée** : `docker compose up -d --build`
   - L'orchestrateur doit être accessible sur `http://localhost:18083`
2. **JDK 21** configuré dans IntelliJ
3. **Maven 3.9+** installé

## Utilisation

1. Ouvrir le projet `comic2pdf-app/` dans IntelliJ IDEA
2. Attendre la résolution des dépendances Maven
3. Sélectionner une configuration dans le menu déroulant Run/Debug
4. Cliquer sur **Run** (▶) ou **Debug** (🐛)

## Notes

- `ORCHESTRATOR_URL` est une **variable d'environnement** (pas une propriété système `-D`)
- Les configurations sont versionnées dans Git pour partage avec l'équipe
- Pour un lancement en ligne de commande sans IDE, utiliser `scripts/run_desktop.ps1` (Windows) ou `scripts/run_desktop.sh` (Linux/macOS)

## Référence

Documentation complète : [docs/dev/setup.md](../docs/dev/setup.md)

