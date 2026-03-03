# RAPPORT_IMPLEMENTATION_SPRINT2_CI_COVERAGE_2026-03-04

**Type** : IMPLEMENTATION  
**Date** : 2026-03-04  
**Auteur(s)** : Équipe comic2pdf-app  
**Généré par IA** : GitHub Copilot  
**Responsable de la submission** : *(à compléter — GitHub handle)*

---

## 1. Contexte et résumé

Sprint 2 du projet `comic2pdf-app` : mise en place des seuils de couverture de code en CI
(anti-régression Python + Java), stabilisation des tests UI TestFX en CI headless via Monocle,
et ajout d'un packaging desktop initial via `jlink` (runtime portable autonome).

Les seuils Python CI appliquent une **tolérance initiale baseline−5** pour absorber les
variations légitimes. Une PR dédiée (`chore/coverage-thresholds-sprint2-stable`) montera
les seuils à baseline−2 une fois la CI stable.

---

## 2. Objectifs du Sprint 2

- [x] Seuils `--cov-fail-under` par service dans la matrice CI GitHub Actions
- [x] `jacoco:check` (profil `coverage-check`) actif en CI pour `desktop-app`
- [x] Tests UI CI headless avec Monocle activé directement (plus de commentaire `# Fallback`)
- [x] `ScreenshotExtension.java` — extension JUnit 5 séparée, propre, sans circularité
- [x] `BaseUiTest.java` — ancre sémantique vide avec `@ExtendWith(ScreenshotExtension.class)`
- [x] Scripts de packaging `jlink` (Windows + Linux)
- [x] Documentation `docs/dev/release.md` + mise à jour `docs/dev/testing.md`

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Type | Description de la modification |
|---------|------|--------------------------------|
| `.github/workflows/ci.yml` | Modifié | Matrice Python → `include` avec `cov_min` par service ; `--cov-fail-under` ; `mvn clean verify -Pcoverage -Pcoverage-check` ; Monocle activé directement ; upload `htmlcov` + `jacoco-xml` |
| `desktop-app/src/test/java/com/comic2pdf/desktop/ui/ScreenshotExtension.java` | **Nouveau** | Extension JUnit 5 `TestExecutionExceptionHandler` ; capture sur FX thread via `CompletableFuture` + `Platform.runLater` ; `new ArrayList<>(Window.getWindows())` copie défensive |
| `desktop-app/src/test/java/com/comic2pdf/desktop/ui/BaseUiTest.java` | Modifié | Remplacement intégral — ancre sémantique vide avec `@ExtendWith(ScreenshotExtension.class)` ; suppression de `testFailed`, `captureScreenshotOnFailure`, `markTestAsFailed` |
| `docs/dev/testing.md` | Modifié | Tableau baseline Sprint 2 (5 colonnes) ; section différence local vs CI ; commande JaCoCo CI mise à jour ; section Tests UI CI Monocle Sprint 2 |
| `scripts/package_desktop_jlink.ps1` | **Nouveau** | Script PowerShell jlink + fat-JAR + run.bat + Compress-Archive |
| `scripts/package_desktop_jlink.sh` | **Nouveau** | Script Bash jlink + fat-JAR + run.sh + zip |
| `docs/dev/release.md` | **Nouveau** | Guide de release : prérequis jmods Gluon, commandes Windows/Linux, structure output, jpackage futur |

### Sous-classes `BaseUiTest` — non modifiées

`MainAppUiTest`, `JobsUiTest`, `DuplicatesUiTest`, `ConfigUiTest` héritent de `BaseUiTest`
et reçoivent automatiquement `@ExtendWith(ScreenshotExtension.class)` via l'héritage JUnit 5.
**Aucune modification requise** dans ces fichiers.

---

## 4. Seuils appliqués

### Python — matrice CI (`.github/workflows/ci.yml`)

| Service | Baseline Sprint 1 | Seuil CI Sprint 2 (baseline−5) | Objectif baseline−2 | PR de montée |
|---------|------------------|-------------------------------|---------------------|--------------|
| `prep-service` | 85.30% | **80%** | 83% | `chore/coverage-thresholds-sprint2-stable` |
| `ocr-service` | 88.52% | **83%** | 86% | `chore/coverage-thresholds-sprint2-stable` |
| `orchestrator` | 66.36% | **61%** | 64% | `chore/coverage-thresholds-sprint2-stable` |

**Justification tolérance baseline−5** : absorber les variations légitimes (tests flaky,
variations de version de dépendances) lors de la première itération CI. La PR
`chore/coverage-thresholds-sprint2-stable` mettra à jour simultanément `ci.yml` + `docs/dev/testing.md`
pour monter aux seuils baseline−2 dès que la CI sera stable sur 5 runs consécutifs.

### Java — JaCoCo `coverage-check` (`desktop-app/pom.xml`)

| Métrique | Seuil actuel (baseline−2) | Baseline mesurée |
|----------|--------------------------|-----------------|
| LINE | 28% (0.28) | 30.16% |
| BRANCH | 15% (0.15) | 17.39% |

> Ces seuils sont déjà configurés dans le profil `coverage-check` depuis le Sprint précédent.
> Le changement Sprint 2 est d'activer ce profil **en CI** via `mvn clean verify -Pcoverage -Pcoverage-check`.

**Exclusions Phase 1 (justifiées)** :
- `com.comic2pdf.desktop.model.*` — JavaFX properties, getters/setters triviaux
- `com.comic2pdf.desktop.ui.controller.*` — UI glue, non testable unitairement
- `com.comic2pdf.desktop.MainApp` — point d'entrée JavaFX

---

## 5. Architecture `ScreenshotExtension`

```
Thread JUnit (test échoué)
  └─ handleTestExecutionException(ctx, throwable)
       ├─ CompletableFuture<Void> future = new CompletableFuture<>()
       ├─ Platform.runLater(() -> {
       │      List<Window> windows = new ArrayList<>(Window.getWindows()); // copie défensive
       │      for (Window w : windows) {
       │          if (w instanceof Stage s && s.isShowing()) captureStage(ctx, s);
       │      }
       │      future.complete(null);
       │  })
       ├─ future.get(5, SECONDS)
       │      catch TimeoutException | IllegalStateException → silencieux (FX non démarré)
       │      catch ExecutionException → log (capture échouée)
       │      catch InterruptedException → interrupt()
       └─ throw throwable  ← TOUJOURS relancé
```

---

## 6. Étapes pour reproduire

```bash
# Tests Python avec seuils CI
cd services/prep-service
pytest -q --cov=app --cov-fail-under=80

# Tests Java avec JaCoCo check
cd desktop-app
mvn clean verify -Pcoverage -Pcoverage-check

# Tests UI headless (Linux avec Xvfb)
xvfb-run -a mvn -q -Pui-tests test \
  -Dtestfx.headless=true -Dprism.order=sw \
  -Dglass.platform=Monocle -Dmonocle.platform=Headless

# Packaging jlink (Windows)
$env:JAVAFX_JMODS_PATH = "C:\tools\javafx-jmods-21.0.4"
.\scripts\package_desktop_jlink.ps1
```

---

## 7. Fichiers modifiés / chemins pertinents

- `.github/workflows/ci.yml`
- `desktop-app/src/test/java/com/comic2pdf/desktop/ui/ScreenshotExtension.java` *(nouveau)*
- `desktop-app/src/test/java/com/comic2pdf/desktop/ui/BaseUiTest.java`
- `docs/dev/testing.md`
- `scripts/package_desktop_jlink.ps1` *(nouveau)*
- `scripts/package_desktop_jlink.sh` *(nouveau)*
- `docs/dev/release.md` *(nouveau)*

---

## 8. Liens vers PR / issues

- PR : À renseigner
- Issues : À renseigner
- PR de montée des seuils : branche `chore/coverage-thresholds-sprint2-stable`

---

## 9. Contact pour questions

Ouvrir une issue dans le dépôt et taguer `@team-architecture`.

---

## Annexe — Checklist PR

- [x] Rapport conforme au pattern `RAPPORT_<TYPE>_YYYY-MM-DD.md`
- [x] Placé dans `docs/ia/rapports-execution/`
- [x] Basé sur `docs/ia/templates/rapport_template.md`
- [ ] Au moins 1 reviewer humain assigné *(à compléter)*
- [x] Mention "Généré par IA" + outil/agent : **GitHub Copilot**
- [x] Sections minimales complètes (titre, date, auteur, résumé, étapes, fichiers, liens PR)

