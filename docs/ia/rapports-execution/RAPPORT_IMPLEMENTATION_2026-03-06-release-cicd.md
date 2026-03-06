# RAPPORT_IMPLEMENTATION_2026-03-06-release-cicd

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Automatisation packaging & distribution — GitHub Actions CI/CD Release |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-03-06` |
| **Auteur(s)** | équipe comic2pdf-app |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | À compléter lors de la soumission |

---

## 2. Contexte et résumé

Le dépôt `comic2pdf-app` disposait d'un workflow CI existant (`ci.yml`) couvrant les tests Python/Java et les audits de sécurité, mais aucune automatisation de packaging et de distribution n'était en place. Cette implémentation ajoute un workflow `release.yml` qui publie automatiquement les images Docker sur Docker Hub et crée une GitHub Release à chaque tag `vX.Y.Z`. Le workflow CI existant est étendu avec des jobs de validation Docker build (sans publication) et de validation jpackage pour l'application desktop JavaFX.

---

## 3. Description des changements

### Fichiers créés / modifiés

| Fichier | Type | Description de la modification |
|---|---|---|
| `.github/workflows/ci.yml` | Modifié | Ajout de 2 jobs : `docker-build` (validation sans push, matrice 3 services) et `java-installer-build` (validation jpackage CI, `continue-on-error`) |
| `.github/workflows/release.yml` | **Nouveau** | Workflow release complet : docker-publish (matrice 3 services), docker-digests-merge, java-installer (3 OS), github-release |
| `docs/release/publishing.md` | **Nouveau** | Guide complet : procédure release, artefacts, secrets, troubleshooting, prochaines étapes |
| `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_2026-03-06-release-cicd.md` | **Nouveau** | Ce rapport |

### Scan repo — résultats

| Cible demandée | Résultat réel | Action prise |
|---|---|---|
| `orchestrator/Dockerfile` | ✅ `services/orchestrator/Dockerfile` | Chemin corrigé dans la matrice |
| `prep-service/Dockerfile` | ✅ `services/prep-service/Dockerfile` | Chemin corrigé dans la matrice |
| `ocr-service/Dockerfile` | ✅ `services/ocr-service/Dockerfile` | Chemin corrigé dans la matrice |
| `api/Dockerfile` | ❌ N'existe pas | Remplacé par les 3 services réels (pas de 4e service backend) |
| CLI PyPI (`pyproject.toml`) | ❌ Absent | Documenté "en attente" dans `publishing.md` |
| Module desktop JavaFX | ✅ `desktop-app/` | Job jpackage activé (`continue-on-error`) |

### Variables d'environnement / secrets ajoutés

| Variable/Secret | Workflow | Valeur/Usage |
|---|---|---|
| `DOCKERHUB_NAMESPACE` (env) | `ci.yml`, `release.yml` | `fturleque81` |
| `IMAGE_PREFIX` (env) | `ci.yml`, `release.yml` | `comic2pdf` |
| `DOCKERHUB_USERNAME` (secret) | `release.yml` | Login Docker Hub |
| `DOCKERHUB_TOKEN` (secret) | `release.yml` | Token PAT Docker Hub |
| `GITHUB_TOKEN` (standard) | `release.yml` | Création GitHub Release |

---

## 4. Architecture des workflows

### ci.yml — jobs ajoutés

```
Job 6 : docker-build
  matrix: [orchestrator, prep-service, ocr-service]
  → docker/setup-buildx-action@v3
  → docker/build-push-action@v6 (push: false, cache GHA)

Job 7 : java-installer-build (ubuntu-latest, continue-on-error)
  → setup-java@v4 (Java 21 temurin)
  → mvn package -DskipTests
  → jpackage --type deb (validation)
```

### release.yml — flux complet

```
docker-publish (matrix × 3 services)
  → login Docker Hub
  → docker/metadata-action (semver + latest + sha)
  → build+push linux/amd64
  → upload docker-digests-<service>.txt

docker-digests-merge (needs: docker-publish)
  → fusion 3 fichiers → docker-digests.txt

java-installer (matrix: ubuntu/windows/macos, continue-on-error)
  → mvn package -DskipTests
  → jpackage (deb/exe/dmg) + sha256sum

github-release (needs: docker-digests-merge + java-installer)
  → softprops/action-gh-release@v2
  → generate_release_notes: true
  → attache docker-digests.txt + installers + checksums
```

---

## 5. Étapes pour reproduire / commandes exécutées

```powershell
# Déclencher une release
git tag v1.0.0
git push origin v1.0.0

# Valider les builds Docker localement
docker build -t test-orchestrator services/orchestrator/
docker build -t test-prep-service services/prep-service/
docker build -t test-ocr-service services/ocr-service/

# Supprimer un tag mal formé
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

### Résultats des tests

| Module | Statut CI | Remarque |
|---|---|---|
| `prep-service` | ✅ non modifié | Jobs existants préservés |
| `ocr-service` | ✅ non modifié | Jobs existants préservés |
| `orchestrator` | ✅ non modifié | Jobs existants préservés |
| `desktop-app` | ✅ non modifié | Jobs existants préservés |
| `docker-build` (CI) | Nouveau job ajouté | Non encore exécuté en CI |
| `java-installer-build` (CI) | Nouveau job ajouté | `continue-on-error: true` |

---

## 6. Points d'attention / Limitations

- **PyPI non activé** : aucun `pyproject.toml`. Le job PyPI n'est pas créé pour éviter un placeholder cassé. À activer dès que `tools/pyproject.toml` sera créé.
- **linux/arm64 désactivé** : les Dockerfiles utilisent des binaires système (`tesseract`, `7z`, `ghostscript`) dont la compatibilité ARM64 n'a pas été validée. Documenté comme "next step".
- **jpackage conditionnel** : `continue-on-error: true` — le `pom.xml` ne produit pas encore de fat JAR. Les installers seront attachés à la release uniquement quand `maven-assembly-plugin` ou `maven-shade-plugin` sera configuré.
- **Signature installers** : non activée (nécessite des certificats codesign macOS / signtool Windows). Documenté comme "next step".
- **SBOM** : non activé dans cette itération. Documenté comme "next step".
- **4e service `api`** : n'existe pas dans le dépôt. La matrice contient uniquement les 3 services réels.

---

## 7. Tableau récapitulatif

| Cible | Artefact | Destination | Déclencheur |
|---|---|---|---|
| orchestrator | `fturleque81/comic2pdf-orchestrator:X.Y.Z` | Docker Hub | Tag `vX.Y.Z` |
| prep-service | `fturleque81/comic2pdf-prep-service:X.Y.Z` | Docker Hub | Tag `vX.Y.Z` |
| ocr-service | `fturleque81/comic2pdf-ocr-service:X.Y.Z` | Docker Hub | Tag `vX.Y.Z` |
| docker-digests.txt | Digests SHA256 des images | GitHub Release + artefact CI | Tag `vX.Y.Z` |
| desktop .deb/.exe/.dmg | Installer natif + checksum SHA256 | GitHub Release + artefact CI | Tag `vX.Y.Z` (fat JAR requis) |
| PyPI | — | — | ⏳ En attente (`pyproject.toml` requis) |

---

## 8. Liens et références

- Workflow release : `.github/workflows/release.yml`
- Workflow CI (modifié) : `.github/workflows/ci.yml`
- Guide publishing : `docs/release/publishing.md`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`

---

## 9. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

