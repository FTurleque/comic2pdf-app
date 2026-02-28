# Git Commit Instructions — comic2pdf-app

Ce document définit les conventions de commit à utiliser dans ce dépôt. Objectifs : historique lisible, PR faciles à relire, releases plus propres.

## 1) Principes

- **Un commit = une intention** (un changement logique).
- **Commits atomiques** : un commit doit idéalement garder le projet compilable/tests passants.
- **Éviter les commits fourre-tout** (“fix”, “wip”, “update”).
- **Message clair** : on doit comprendre *quoi* et *pourquoi* sans ouvrir le diff.

## 2) Format des messages (Conventional Commits)

Format :

```
<type>(<scope>): <subject>
```

- `type` obligatoire
- `scope` recommandé (module/zone)
- `subject` court, à l’impératif, sans point final

### Types autorisés

- `feat` : nouvelle fonctionnalité utilisateur
- `fix` : correction de bug
- `refactor` : refacto sans changement fonctionnel
- `perf` : amélioration performance
- `test` : ajout/modif tests uniquement
- `docs` : documentation uniquement
- `build` : build / dépendances / Maven / Dockerfile
- `chore` : tâches diverses (scripts, format, nettoyage, non-fonctionnel)
- `ci` : uniquement si tu ajoutes du CI (actuellement **à éviter**)
- `revert` : revert d’un commit

### Scopes recommandés (exemples repo)

- `desktop` (JavaFX)
- `orchestrator`
- `prep-service`
- `ocr-service`
- `docker`
- `docs`
- `tests`
- `config`

## 3) Exemples de commits (bons)

### Desktop / UI
- `feat(desktop): add FXML-based main view with tabs`
- `refactor(desktop): move controllers to ui.controller package`
- `fix(desktop): prevent jobs auto-refresh during ui tests`
- `test(desktop): add TestFX ui-tests profile and smoke tests`

### Orchestrator / services
- `fix(orchestrator): reject invalid ZIP/RAR signatures`
- `feat(orchestrator): expose /jobs and /metrics via http.server`
- `refactor(prep-service): extract images_to_pdf into core module`
- `test(ocr-service): mock subprocess calls for OCR pipeline`

### Docs / scripts
- `docs: add full user and developer documentation`
- `chore: add run_desktop scripts for PowerShell and bash`

### Licence
- `docs: add MIT license and third-party notices`

## 4) Breaking changes

Si un changement casse un contrat public (API, format de fichier, CLI, endpoints, structure des dossiers), utiliser :

- `feat(scope)!: ...`  
et ajouter une section BREAKING CHANGE dans le message de commit :

```
feat(orchestrator)!: change jobKey format to include tool versions

BREAKING CHANGE: jobKey now includes tool versions; existing outputs are not reused.
```

## 5) Taille des commits

- Préférer **petits commits** (faciles à review).
- Si un refactor touche beaucoup de fichiers, découper :
  1) `refactor(...)` déplacement/renommage (sans logique)
  2) `refactor(...)` adaptation code
  3) `test(...)` mise à jour tests
  4) `docs(...)` mise à jour doc

## 6) Règles spécifiques au repo (important)

### A) UI JavaFX / FXML
- Séparer commits FXML vs logique si possible :
  - `feat(desktop): add FXML layouts`
  - `feat(desktop): wire controllers to services`
- Les IDs `fx:id` utilisés par TestFX ne doivent pas changer sans mettre à jour les tests dans le même commit.

### B) Tests
- Si un commit modifie un comportement, il doit idéalement inclure :
  - les tests correspondants (ou un commit `test(...)` immédiatement après)
- Les tests UI (TestFX) sont dans le profil `ui-tests` et doivent rester opt-in.

### C) Scripts de lancement
- Toute modification de scripts (PowerShell/Bash) doit être testée et documentée.

## 7) Workflow local (solo-friendly)

- Branche de travail :
  - `feat/<topic>`
  - `fix/<topic>`
  - `docs/<topic>`
  - `refactor/<topic>`
- PR obligatoire vers `main` (pas de push direct si main est protégée).
- Merge recommandé : **squash merge** (1 commit propre dans main).
  - Dans ce cas, le titre de PR doit respecter le format Conventional Commits :
    - ex : `feat(desktop): migrate UI to FXML`

## 8) Checklist avant commit

- `mvn test` (desktop-app) si tu touches Java
- `pytest` si tu touches Python
- docs mise à jour si tu changes un comportement utilisateur
- pas de secrets / tokens dans le code
- message de commit conforme

## 9) Rebase / amend (recommandations)

- Avant PR : rebase sur `main` si nécessaire.
- Utiliser `git commit --amend` pour corriger un message local avant push.
- Éviter `--force` sur branches partagées (et interdit sur main).

## 10) Commandes utiles

Créer un commit :
```bash
git status
git add -A
git commit -m "feat(desktop): add jobs tab with refresh"
```

Amender le dernier commit :
```bash
git commit --amend
```

Voir l’historique compact :
```bash
git log --oneline --decorate --graph -20
```
