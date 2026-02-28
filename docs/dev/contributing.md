# Contribution — comic2pdf-app

Ce guide s'adresse aux développeurs souhaitant contribuer au projet. Il détaille les invariants non négociables, les principes SOLID appliqués au projet, les conventions et le processus de review.

---

## Les 8 invariants non négociables

Ces invariants **ne peuvent pas être violés** sans refactoring explicitement approuvé.

### 1. Pas de réseau externe

Les services Python communiquent **uniquement** entre eux via HTTP interne (`PREP_URL`, `OCR_URL`). Zéro appel Internet. Zéro dépendance cloud.

### 2. Atomicité des écritures

- Toujours écrire en mode `*.tmp` → `os.replace()` (POSIX) ou `Files.move(ATOMIC_MOVE)` (Java).
- Dépôt entrant : `.part` → `.cbz/.cbr`. Ne **jamais** lire un `.part`.
- Utiliser `atomic_write_json()` de `app/utils.py` pour tout JSON d'état.

### 3. Déduplication déterministe

- `jobKey = fileHash__profileHash` — deux SHA-256 séparés par `__`.
- Profil canonique = langues normalisées (tokens triés) + versions des outils.
- `eng+fra` ≡ `fra+eng` → même `profileHash`.
- Décisions autorisées : `USE_EXISTING_RESULT` | `DISCARD` | `FORCE_REPROCESS`.
- Aucune re-soumission sans `decision.json` écrit par l'app Desktop.

### 4. Trois tentatives par étape — recalcul complet

- Sur retry : **supprimer les artefacts** de l'étape précédente avant de recommencer.
- Dépassement du maximum → état `ERROR`, fichier vers `data/error/`.

### 5. Heartbeat et timeout

- Workers écrivent `<job_dir>/prep.heartbeat` ou `ocr.heartbeat` à chaque étape clé.
- `check_stale_jobs()` bascule les jobs périmés en `*_RETRY`.
- Heartbeat absent → stale après `2 × JOB_TIMEOUT_SECONDS` (évite les faux positifs au démarrage).

### 6. Métriques JSON pur

- Compteurs `done`, `error`, `running`, `queued`, `disk_error`, `pdf_invalid`, `input_rejected_size`, `input_rejected_signature` via `update_metrics()`.
- Persistés dans `data/index/metrics.json` à chaque tick. Zéro Prometheus, zéro dépendance externe.

### 7. Bootstrap non-impactant à l'import

- **prep-service / ocr-service** : threads workers démarrés **uniquement** dans `@app.on_event("startup")` FastAPI (pas à l'import).
- **orchestrator** : script pur Python. Démarrage via `if __name__ == "__main__": process_loop()`.
- `process_tick()` est la fonction pure testable (sans sleep). `process_loop()` est la boucle infinie.
- Import de n'importe quel module = **zéro effet de bord** (testabilité garantie).

### 8. Scope strict — une modification, un service

- Une modification dans `ocr-service` ne touche pas `prep-service` sans justification documentée dans la PR.
- Une modification UI dans `desktop-app` ne touche pas la logique Python.
- Respecter la séparation : `MainView`/`JobsView`/`ConfigView` (UI) ↔ `DuplicateService`/`OrchestratorClient`/`ConfigService` (logique).

---

## Principes SOLID appliqués au projet

### S — Single Responsibility (Responsabilité unique)

> Une classe = une seule raison de changer.

**Exemple concret** :
- `DuplicateService` : logique filesystem doublons **uniquement** (lecture rapports, écriture décisions).
- `OrchestratorClient` : communication HTTP avec l'orchestrateur **uniquement**.
- `ConfigService` : persistance `config.json` **uniquement**.
- Si `MainView` faisait à la fois l'UI et la lecture des rapports JSON → violation SRP → refactorer.

### O — Open/Closed (Ouvert/Fermé)

> Ouvert à l'extension, fermé à la modification.

**Exemple concret** :
- Ajouter un nouveau type de décision doublon → étendre `DuplicateDecision` (nouvel enum), pas modifier `DuplicateService.writeDecision()`.
- Ajouter un nouveau compteur de métrique → étendre `update_metrics()` avec un nouveau cas, pas modifier l'infrastructure de persistance.

### L — Liskov Substitution (Substitution de Liskov)

> Les sous-classes doivent être substituables à leurs parents.

**Exemple concret** :
- Si une interface `JobClient` est créée, `OrchestratorClient` doit être substituable sans casser `JobsView`.
- Les implémentations mock dans les tests (`MockOrchestratorClient`) doivent respecter le même contrat.

### I — Interface Segregation (Ségrégation des interfaces)

> Préférer plusieurs interfaces spécifiques plutôt qu'une interface monolithique.

**Exemple concret** :
- Ne pas créer une interface `IDesktopService` qui mélange doublons + jobs + config.
- Créer des interfaces séparées : `IDuplicateService`, `IJobService`, `IConfigService`.

### D — Dependency Inversion (Inversion des dépendances)

> Dépendre des abstractions, pas des implémentations.

**Exemple concret** :
- `MainView` reçoit `DuplicateService` via son constructeur (injection de dépendance).
- `JobsView` reçoit `OrchestratorClient` via son constructeur.
- Les tests peuvent injecter des mocks sans modifier les classes métier.

---

## Compatibilité Windows / Linux

### Règles critiques cross-platform

| Problème | Solution |
|---|---|
| `os.rename()` peut échouer si destination existe (Windows) | Utiliser `os.replace()` à la place |
| Séparateur de chemin | Utiliser `pathlib.Path` en Python, `Path.of()` / `Paths.get()` en Java |
| Rename atomique Java | `Files.move(src, dst, StandardCopyOption.ATOMIC_MOVE)` |
| Fin de ligne | `.gitattributes` configure `text=auto` — ne pas forcer |
| `chmod` / permissions | Ne pas utiliser dans le code partagé Windows/Linux |

### Exemple Python

```python
import os
from pathlib import Path

# ✅ Correct (cross-platform)
tmp = Path(dest).with_suffix(".tmp")
tmp.write_text(content)
os.replace(tmp, dest)  # atomique sur POSIX, best-effort sur Windows

# ❌ Incorrect (Windows peut lever FileExistsError)
os.rename(tmp, dest)
```

### Exemple Java

```java
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

// ✅ Correct
Files.move(tmpPath, destPath, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);

// ❌ Incorrect (non atomique)
tmpPath.toFile().renameTo(destPath.toFile());
```

---

## Checklist PR locale (sans CI)

Avant de soumettre une PR ou un patch, vérifier point par point :

### 🔴 Critique (bloquant)

- [ ] **Compilation Java** : `cd desktop-app && mvn -q test` — zéro erreur
- [ ] **Tests Python** : `pytest -q` dans chaque service modifié — zéro échec
- [ ] **Aucun secret hardcodé** : pas de token, password, clé d'API dans le code
- [ ] **Tests unitaires ajoutés** pour toute logique non triviale (happy path + ≥ 1 cas d'erreur)
- [ ] **Les 8 invariants** ci-dessus sont respectés

### 🟠 Important (fortement recommandé)

- [ ] **Patch-only** : changements limités, listés dans `PATCH_MANIFEST.md`
- [ ] **Javadoc française** : toutes les classes/méthodes publiques avec `@param`, `@return`, `@throws`
- [ ] **Docstrings Python** : toutes les fonctions publiques avec `:param:`, `:return:`, `:raises:`
- [ ] **Conventions de nommage** respectées (voir tableau ci-dessous)
- [ ] **Atomicité** : toute écriture de fichier passe par `os.replace()` ou `atomic_write_json()`
- [ ] **Scope strict** : les modifications sont limitées au(x) service(s) concerné(s)

### 🟡 Recommandé

- [ ] Si UI modifiée (`desktop-app`) : compilation complète vérifiée (`mvn -q -DskipTests package`)
- [ ] Décisions d'architecture documentées dans `docs/ia/rapports-execution/` si significatives
- [ ] `PATCH_MANIFEST.md` mis à jour avec la liste des fichiers modifiés

---

## Conventions de nommage — tableau récapitulatif

| Contexte | Convention | Exemples |
|---|---|---|
| Python — fonctions/variables | `snake_case` | `make_job_key`, `job_timeout_s`, `in_flight` |
| Python — constantes de module | `UPPER_CASE` | `MAX_ATTEMPTS_PREP`, `DATA_DIR`, `OCR_LANG` |
| Python — modules | `snake_case` | `core.py`, `http_server.py`, `utils.py` |
| Python — packages | `snake_case` | `app`, `tests` |
| Java — classes/interfaces | `PascalCase` | `DuplicateService`, `OrchestratorClient`, `AppConfig` |
| Java — méthodes/champs | `camelCase` | `listDuplicates`, `jobKey`, `orchestratorUrl` |
| Java — constantes | `UPPER_CASE` | `DEFAULT_ORCHESTRATOR_URL`, `MAX_RETRY` |
| JSON — clés d'état | `camelCase` | `jobKey`, `updatedAt`, `rawPdf`, `finalPdf` |
| Fichiers data | `snake_case` | `prep.heartbeat`, `state.json`, `decision.json` |
| Nom de fichier Java | `PascalCase` + `.java` | `DuplicateService.java` (1 type public par fichier) |
| Variables d'environnement | `UPPER_CASE` | `PREP_URL`, `OCR_CONCURRENCY`, `LOG_JSON` |

---

## Processus de review

### PR standard (modification de code)

1. Créer une branche depuis `main` : `git checkout -b feat/description-courte`
2. Appliquer les modifications (**patch-only**)
3. Exécuter `.\run_tests.ps1` (ou les tests du module concerné)
4. Remplir `PATCH_MANIFEST.md` avec la liste des fichiers modifiés
5. Ouvrir la PR avec un titre clair et un body décrivant les changements
6. Assigner **au minimum 1 reviewer humain**

### PR contenant du code généré par IA

En plus des étapes ci-dessus :
- Mentionner explicitement dans le body de la PR : **"Généré par IA — GitHub Copilot"** (ou l'outil concerné)
- L'auteur humain responsable est **obligatoirement identifié** (nom + GitHub handle)
- Le reviewer humain doit vérifier manuellement la cohérence du code généré avec les invariants

### PR contenant un rapport IA

Voir la politique complète dans [`.github/instructions/reports-docs.instructions.md`](../../.github/instructions/reports-docs.instructions.md) :
- Rapport placé dans `docs/ia/rapports-execution/` ou `docs/ia/rapports-migration/`
- Nommé `RAPPORT_<TYPE>_YYYY-MM-DD.md`
- Basé sur `docs/ia/templates/rapport_template.md`
- Mention "Généré par IA" + outil dans le rapport

---

## Retour

[← Retour à la documentation développeur](README.md)

