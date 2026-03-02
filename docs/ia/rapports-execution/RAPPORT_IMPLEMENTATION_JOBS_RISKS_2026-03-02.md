# RAPPORT_IMPLEMENTATION_JOBS_RISKS_2026-03-02

**Généré par IA** — GitHub Copilot
**Date :** 2026-03-02
**Auteur / Responsable :** Équipe comic2pdf-app
**Type :** IMPLEMENTATION

---

## Contexte et résumé

Clôture des risques et questions en suspens liés à l'onglet Jobs de l'application desktop
JavaFX (`comic2pdf-app`). Aucun changement de périmètre fonctionnel — corrections de
robustesse, thread-safety et testabilité uniquement.

Six risques identifiés lors de l'implémentation initiale. Bilan : 5 étaient déjà correctement
implémentés, 1 nécessitait une correction (R4 — thread-safety `ConnectivityService`).
Deux suites de tests unitaires manquantes ont été créées.

---

## Description des changements

### R1 — `startedAt`/`endedAt` absents → durée `"N/A"` sans crash ✅ (déjà correct)

`JobDurationUtils.compute(startedAt, endedAt)` retourne `"N/A"` si l'un des horodatages
est `null`, vide, malformé, ou si la durée calculée est négative.

Le stub HTTP de `JobsUiTest` ne fournit pas `startedAt`/`endedAt` (champs absents du JSON).
Le champ "Durée" du panneau détail affiche `"N/A"` sans exception. Aucun changement requis.

### R2 — Pas d'endpoint `/logs` → logs = `errorMessage` + `outPdf` ✅ (déjà correct)

Zone "Logs / Sortie" du panneau détail : section `=== Error ===` si `errorMessage` non vide,
section `=== Output PDF ===` si `outPdf` non vide.

**Point d'extensibilité** : `JobDetailPanelController.onReloadDetail()` est le seul point à
modifier si un endpoint `/jobs/{id}/logs` est ajouté. Le panneau FXML et la méthode
`setLogSections(error, output)` restent inchangés.

### R3 — Compatibilité `JobsUiTest` (refresh async < 3s) ✅ (déjà correct)

`JobsController.onRefreshJobs()` utilise `Task<List<JobRow>>` + thread daemon.
- Pas de `Thread.sleep` dans le flux.
- `Platform.runLater` uniquement pour la mise à jour UI (via `task.setOnSucceeded`).
- Timeout HTTP : 5s (le stub répond en < 100ms).
- `TestableMainApp.jobsAutoRefreshOverride = false` désactive le poll automatique en test.

### R4 — Thread-safety `ConnectivityService` → **CORRIGÉ** ⚠️→✅

**Problème** : `ping()` lisait `online.get()` (BooleanProperty JavaFX) depuis le thread daemon
du scheduler — violation du modèle de threading JavaFX (les Property ne sont pas thread-safe).

**Correction appliquée dans `ConnectivityService.java`** :

| Avant | Après |
|---|---|
| `if (online.get()) return;` dans `ping()` | `if (!offlineFlag.get()) return;` (AtomicBoolean) |
| `isOnline()` → `online.get()` | `isOnline()` → `!offlineFlag.get()` |
| `markOnline()` : assert FX thread uniquement | Guard auto-reroute via `Platform.runLater` |
| `markOffline()` : assert FX thread uniquement | Guard auto-reroute via `Platform.runLater` |

`offlineFlag` (AtomicBoolean) est mis à jour en cohérence avec `online` (BooleanProperty)
dans `markOnline`/`markOffline`, toujours sur le FX thread.

### R5 — FXML incomplet → `fx:id` manquants ✅ (corrigé session précédente)

`JobsView.fxml` et `JobDetailPanel.fxml` contiennent maintenant tous les `fx:id` attendus
par `JobsController` et `JobDetailPanelController`.

### R6 — Taille controller / SRP ✅ (dans les limites)

`JobsController` = 382 lignes (< 400). Extraction validée :
`JobDetailPanelController` (209 lignes via `<fx:include>`) +
`ConnectivityService` (ping/retry/backoff) + `JobDurationUtils` (calcul durée).

---

## Tests unitaires créés

| Fichier | Cas couverts |
|---|---|
| `test/util/JobDurationUtilsTest.java` | 11 cas : `null`, vide, malformed, négatif, valides (R1) |
| `test/service/ConnectivityServiceTest.java` | 4 cas : état initial, lecture thread non-FX, shutdown idempotent, setOnComeOnline null (R4) |

---

## Étapes pour reproduire / commandes exécutées

```powershell
# Depuis la racine du repo
cd desktop-app
mvn test
# Attendu : Tests run: 44+, Failures: 0, Errors: 0, BUILD SUCCESS
```

---

## Checklist de validation

### Tests automatisés
- [ ] `mvn test` → 44+ tests, 0 failure, BUILD SUCCESS
- [ ] `JobDurationUtilsTest` : `tousDeuxVides()` passe (cas stub JobsUiTest)
- [ ] `ConnectivityServiceTest` : `isOnlineThreadSafe()` passe (pas d'exception hors FX thread)

### Test manuel offline
1. Lancer l'app avec `ORCHESTRATOR_URL=http://invalid:9999`
2. Bannière jaune "Orchestrateur hors-ligne" visible
3. Table conservée (pas vidée)
4. Démarrer l'orchestrateur, cliquer "Réessayer" → bannière disparaît

### Test sélection job
1. Sélectionner une ligne → panneau détail rempli
2. `startedAt` absent → Durée = "N/A" (pas de crash)
3. `errorMessage` non vide → section `=== Error ===` dans zone logs
4. Bouton "Copier erreur" → presse-papiers

### Test `stop()`
- Fermeture fenêtre → `scheduledRefresh.cancel()` + `connectivityService.shutdown()`
- Aucun thread zombie (vérifier via JMX ou logs)

---

## Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `service/ConnectivityService.java` | **Modifié** — R4 : AtomicBoolean offlineFlag, guard markOnline/markOffline |
| `test/util/JobDurationUtilsTest.java` | **Créé** — 11 cas R1 |
| `test/service/ConnectivityServiceTest.java` | **Créé** — 4 cas R4 |
| `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_JOBS_RISKS_2026-03-02.md` | **Créé** |

---

## Liens vers PR / issues

À renseigner lors de la création de la PR.

---

## Contact

Pour des questions sur cette politique, ouvrir une issue dans le dépôt et taguer
`@team-architecture`.

