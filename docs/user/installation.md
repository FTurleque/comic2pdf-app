# Installation — comic2pdf-app

Ce guide explique comment installer et démarrer `comic2pdf-app` dans ses deux modes : **Docker** (recommandé) et **Desktop JavaFX**.

---

## Prérequis système

### Mode Docker

| Logiciel | Version minimale | Lien |
|---|---|---|
| Docker Desktop | 4.x | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Docker Compose | v2 (intégré) | Inclus dans Docker Desktop |

> **Linux** : Docker Engine suffit (sans Docker Desktop). Vérifier que `docker compose` (v2) est disponible.

### Mode Desktop JavaFX (optionnel)

| Logiciel | Version minimale | Vérification |
|---|---|---|
| Java (JDK) | 21 | `java --version` |
| Maven | 3.9+ | `mvn --version` |

> L'application desktop nécessite également que la **stack Docker soit lancée** pour communiquer avec l'orchestrateur.

---

## Installation en mode Docker

### Étape 1 — Récupérer le dépôt

```powershell
# Windows PowerShell
git clone <url-du-depot>
cd comic2pdf-app
```

```bash
# Linux / macOS
git clone <url-du-depot>
cd comic2pdf-app
```

### Étape 2 — Lancer la stack

```powershell
# Windows PowerShell
docker compose up -d --build
```

```bash
# Linux / macOS
docker compose up -d --build
```

Docker Compose construit les images et démarre les 3 services :

| Service | Port local exposé | Port interne |
|---|---|---|
| `prep-service` | `18081` | `8080` |
| `ocr-service` | `18082` | `8080` |
| `orchestrator` | `18083` | `8080` |

### Étape 3 — Vérifier que les services sont opérationnels

```powershell
# Windows PowerShell — vérifier les 3 services
Invoke-RestMethod http://localhost:18081/info
Invoke-RestMethod http://localhost:18082/info
Invoke-RestMethod http://localhost:18083/metrics
```

```bash
# Linux / macOS
curl http://localhost:18081/info
curl http://localhost:18082/info
curl http://localhost:18083/metrics
```

Réponse attendue pour `/info` (prep-service ou ocr-service) :

```json
{
  "service": "prep-service",
  "versions": {
    "7z": "21.07",
    "img2pdf": "0.5.1"
  }
}
```

Réponse attendue pour `/metrics` :

```json
{
  "done": 0,
  "error": 0,
  "running": 0,
  "queued": 0,
  "disk_error": 0,
  "pdf_invalid": 0,
  "input_rejected_size": 0,
  "input_rejected_signature": 0,
  "updatedAt": "2026-02-28T00:00:00Z"
}
```

### Étape 4 — Tester avec un premier fichier

```powershell
# Windows PowerShell
Copy-Item "C:\mes-bd\MonComic.cbz" ".\data\in\MonComic.cbz.part"
Rename-Item ".\data\in\MonComic.cbz.part" "MonComic.cbz"
```

```bash
# Linux / macOS
cp "/mes-bd/MonComic.cbz" "./data/in/MonComic.cbz.part"
mv "./data/in/MonComic.cbz.part" "./data/in/MonComic.cbz"
```

Le PDF apparaîtra dans `data/out/` sous la forme `MonComic__job-<jobKey>.pdf`.

---

## Build et exécution de l'application Desktop

### Prérequis

S'assurer que Java 21 et Maven 3.9+ sont installés :

```powershell
# Windows PowerShell
java --version
# attendu : openjdk 21.x.x ...

mvn --version
# attendu : Apache Maven 3.9.x ...
```

### Build et lancement

```powershell
# Windows PowerShell
cd desktop-app
mvn -q -DskipTests package
mvn -q javafx:run
```

```bash
# Linux / macOS
cd desktop-app
mvn -q -DskipTests package
mvn -q javafx:run
```

### Configuration de l'URL de l'orchestrateur

L'application Desktop doit connaître l'URL de l'orchestrateur pour se connecter. Deux méthodes :

#### Méthode 1 — Variable d'environnement (au lancement)

```powershell
# Windows PowerShell
$env:ORCHESTRATOR_URL = "http://localhost:18083"
mvn -q javafx:run
```

```bash
# Linux / macOS
ORCHESTRATOR_URL=http://localhost:18083 mvn -q javafx:run
```

#### Méthode 2 — Onglet Configuration dans l'interface

1. Lancer l'application Desktop
2. Cliquer sur l'onglet **Configuration**
3. Modifier le champ **URL orchestrateur** : `http://localhost:18083`
4. Cliquer sur **Appliquer**

La configuration est persistée dans :
- **Windows** : `%APPDATA%\comic2pdf\config.json`
- **Linux / macOS** : `~/.comic2pdf/config.json`

---

## Note sur le mode CLI/local (sans Docker)

Le mode CLI et watch-folder local (sans Docker) est **intentionnellement reporté** à une prochaine itération. Il nécessiterait la présence des binaires `7z`, `ocrmypdf`, `tesseract` et `ghostscript` dans le PATH système, ainsi qu'une gestion manuelle des ports HTTP inter-services. Cette fonctionnalité est marquée **à venir**.

---

## Retour

[← Retour à la documentation utilisateur](README.md)

