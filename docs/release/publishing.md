# Guide de publication — comic2pdf-app

> Documentation de la politique de release et distribution automatisée.
> Maintenu par : équipe comic2pdf-app

---

## Vue d'ensemble

| Déclencheur | Action |
|---|---|
| PR / push `main` | CI verte + build Docker (sans publish) + validation jpackage |
| Tag `vX.Y.Z` | Images Docker Hub publiées + GitHub Release créée + installers attachés |

---

## 1. Créer une release

### Procédure standard

```bash
# 1. S'assurer que main est propre et les tests passent
git checkout main
git pull origin main

# 2. Créer et pousser le tag (déclenche release.yml automatiquement)
git tag v1.2.3
git push origin v1.2.3
```

Le tag doit respecter le pattern `v*` (ex: `v1.0.0`, `v1.2.3`, `v2.0.0-beta.1`).

> **Pré-releases** : un tag contenant `-` (ex: `v1.0.0-beta.1`) est automatiquement
> marqué `prerelease: true` dans GitHub Releases.

### Résultat attendu après push du tag

1. Le workflow `release.yml` se déclenche sur GitHub Actions.
2. 3 images Docker sont buildées et publiées sur Docker Hub.
3. Un fichier `docker-digests.txt` est généré et uploadé en artefact.
4. Les installers jpackage sont buildés (Linux/Windows/macOS) si le fat JAR est disponible.
5. Une GitHub Release `vX.Y.Z` est créée automatiquement avec :
   - Notes de release générées automatiquement (changelog)
   - `docker-digests.txt` attaché
   - Installers + checksums SHA256 attachés (si jpackage OK)

---

## 2. Artefacts publiés

### Docker Hub

| Service | Image | Tags publiés |
|---|---|---|
| orchestrator | `fturleque81/comic2pdf-orchestrator` | `X.Y.Z` · `latest` · `sha-XXXXXXX` |
| prep-service | `fturleque81/comic2pdf-prep-service` | `X.Y.Z` · `latest` · `sha-XXXXXXX` |
| ocr-service  | `fturleque81/comic2pdf-ocr-service`  | `X.Y.Z` · `latest` · `sha-XXXXXXX` |

Architecture publiée : `linux/amd64`

> **linux/arm64** : non activé dans cette itération (nécessite validation des Dockerfiles
> avec les binaires Tesseract/7z sur ARM). À activer dans une PR dédiée.

```bash
# Exemple de pull après une release v1.2.3
docker pull fturleque81/comic2pdf-orchestrator:1.2.3
docker pull fturleque81/comic2pdf-prep-service:1.2.3
docker pull fturleque81/comic2pdf-ocr-service:1.2.3

# Utiliser latest (dernière version stable)
docker pull fturleque81/comic2pdf-orchestrator:latest
```

### GitHub Release

Fichiers attachés à chaque release GitHub :

| Fichier | Description |
|---|---|
| `docker-digests.txt` | Digests SHA256 des images Docker publiées |
| `comic2pdf-desktop-X.Y.Z.deb` | Installer Linux (Debian/Ubuntu) |
| `comic2pdf-desktop-X.Y.Z.exe` | Installer Windows |
| `comic2pdf-desktop-X.Y.Z.dmg` | Installer macOS |
| `checksums-*.sha256` | Checksums SHA256 des installers |

> Les installers sont générés par `jpackage` (Java 21) et nécessitent que le module
> `desktop-app` produise un fat JAR. Voir section [Prérequis jpackage](#4-prérequis-jpackage).

### PyPI — CLI comic2pdf

| Package | Index | Tags publiés |
|---|---|---|
| `comic2pdf` | [pypi.org/project/comic2pdf](https://pypi.org/project/comic2pdf/) | `X.Y.Z` |

```bash
# Installation du CLI
pip install comic2pdf==1.2.3

# Utilisation
comic2pdf mon-fichier.cbz --lang fra+eng --out ./output/
comic2pdf mon-fichier.cbr --no-ocr --out ./output/
comic2pdf --check-deps
```

Le package est publié depuis `pyproject.toml` (racine du dépôt) via **Trusted Publishing OIDC** (pas de secret requis côté GitHub, configuration requise sur pypi.org). Voir section [Secrets requis](#3-secrets-requis).

---

## 3. Secrets requis

### Obligatoires (Docker Hub)

| Secret GitHub | Valeur attendue | Où configurer |
|---|---|---|
| `DOCKERHUB_USERNAME` | Nom d'utilisateur Docker Hub (`fturleque81`) | Settings → Secrets → Actions |
| `DOCKERHUB_TOKEN`   | Personal Access Token Docker Hub (Read/Write) | Settings → Secrets → Actions |

**Créer un token Docker Hub :**
1. Connexion sur [hub.docker.com](https://hub.docker.com)
2. Account Settings → Security → New Access Token
3. Scope : `Read, Write, Delete`
4. Copier le token et l'ajouter comme secret `DOCKERHUB_TOKEN` dans le dépôt GitHub.

### GITHUB_TOKEN

Aucune configuration nécessaire. Le `GITHUB_TOKEN` standard est utilisé avec
`permissions: contents: write` pour créer la GitHub Release.

### PyPI — Trusted Publishing OIDC (recommandé, aucun secret GitHub requis)

1. Connexion sur [pypi.org](https://pypi.org) → Account → Publishing → Add a new publisher
2. Paramètres :
   - **Owner** : `fturleque81` (ou l'organisation GitHub)
   - **Repository name** : `comic2pdf-app`
   - **Workflow filename** : `release.yml`
   - **Environment** : *(laisser vide)*
3. Aucun secret GitHub à configurer — le token OIDC est généré automatiquement.

**Fallback (si OIDC non configuré)** : ajouter `PYPI_API_TOKEN` dans les secrets GitHub
et décommenter les lignes `with: password:` dans le job `pypi-publish` de `release.yml`.

---

## 4. Prérequis jpackage

Le job `java-installer` dans `release.yml` nécessite un **fat JAR**. Il est désormais
produit automatiquement par `maven-assembly-plugin` (configuré dans `desktop-app/pom.xml`) :

```
desktop-app/target/desktop-app-X.Y.Z-jar-with-dependencies.jar
```

Produit lors de `mvn package` (phase `package`, goal `assembly:single`).

---

## 5. Troubleshooting

### Tag mal formé

**Symptôme** : Le workflow `release.yml` ne se déclenche pas.

**Cause** : Le tag ne respecte pas le pattern `v*`.

**Solution** :
```bash
# Supprimer le mauvais tag
git tag -d mauvais-tag
git push origin :refs/tags/mauvais-tag

# Recréer avec le bon format
git tag v1.2.3
git push origin v1.2.3
```

---

### Échec login Docker Hub

**Symptôme** : `Error: unauthorized: incorrect username or password`

**Causes possibles** :
- Secret `DOCKERHUB_USERNAME` ou `DOCKERHUB_TOKEN` manquant/incorrect.
- Token Docker Hub expiré.

**Solution** :
1. Vérifier Settings → Secrets → Actions dans le dépôt GitHub.
2. Regénérer un token sur Docker Hub si nécessaire.
3. Re-lancer le workflow depuis l'onglet Actions.

---

### Échec build Docker (Dockerfile manquant)

**Symptôme** : `ERROR: failed to read dockerfile`

**Cause** : Chemin incorrect dans la matrice du workflow.

**Solution** : Vérifier que les chemins dans `release.yml` correspondent à la structure réelle :
```
services/orchestrator/Dockerfile  ✅
services/prep-service/Dockerfile   ✅
services/ocr-service/Dockerfile    ✅
```

---

### jpackage — JAR non trouvé

**Symptôme** : `⚠ Aucun fat JAR trouvé — jpackage ignoré`

**Cause** : `desktop-app/pom.xml` ne configure pas de fat JAR.

**Solution** : Voir [Prérequis jpackage](#4-prérequis-jpackage).

---

### PyPI OIDC non configuré

**Symptôme** : `Error: PyPI Trusted Publishing not configured`

**Cause** : La configuration Trusted Publishing n'a pas été faite sur pypi.org.

**Solution** :
1. Aller sur pypi.org → Account → Publishing
2. Ajouter un nouveau publisher avec : owner = nom-org, repo = `comic2pdf-app`, workflow = `release.yml`
3. Ou utiliser le fallback avec `PYPI_API_TOKEN` (secret GitHub).

---

## 6. Prochaines étapes (next steps)

| Priorité | Tâche | Statut |
|---|---|---|
| ✅ Fait | `pyproject.toml` créé → CLI PyPI activé | Livré |
| ✅ Fait | `maven-assembly-plugin` configuré → fat JAR + jpackage | Livré |
| 🟠 Moyenne | Configurer Trusted Publishing OIDC sur pypi.org | Manuel (côté PyPI) |
| 🟠 Moyenne | Ajouter `linux/arm64` dans la matrice Docker (valider ARM Dockerfiles) | À faire |
| 🟠 Moyenne | Activer la signature des installers (codesign macOS, signtool Windows) | À faire |
| 🟡 Basse | Ajouter génération SBOM (CycloneDX ou SPDX) attaché à la release | À faire |
| 🟡 Basse | Configurer Dependabot auto-merge pour les mises à jour patch | À faire |

---

## 7. Liens utiles

- Workflow CI : `.github/workflows/ci.yml`
- Workflow Release : `.github/workflows/release.yml`
- Audit dépendances : `.github/workflows/dependency-audit.yml`
- Docker Hub : [hub.docker.com/u/fturleque81](https://hub.docker.com/u/fturleque81)
- GitHub Releases : `https://github.com/<org>/comic2pdf-app/releases`

