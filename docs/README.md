# Documentation comic2pdf-app

Bienvenue dans la documentation complète de **comic2pdf-app**, l'outil de conversion d'archives BD (`.cbz` / `.cbr`) en PDF avec texte sélectionnable (OCR).

---

## Sommaire

| Section | Description |
|---|---|
| [📗 Documentation utilisateur](user/README.md) | Installation, utilisation, résolution de problèmes |
| [🔧 Documentation développeur](dev/README.md) | Architecture, setup dev, tests, opérations, contribution |
| [🤖 Documentation IA](ia/README.md) | Rapports d'implémentation et analyses générées par l'IA |

---

## Quick start Docker

### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) ou Docker Engine (Linux)

### Lancement

```bash
# 1. Cloner le dépôt
git clone <url-du-depot>
cd comic2pdf-app

# 2. Lancer la stack complète
docker compose up -d --build

# 3. Vérifier que les services tournent
curl http://localhost:18081/info   # prep-service
curl http://localhost:18082/info   # ocr-service
curl http://localhost:18083/metrics # orchestrator
```

Déposer ensuite un fichier dans `data/in/` et récupérer le PDF dans `data/out/`.

> ⚠️ Toujours copier d'abord en `.part`, puis renommer — voir [usage.md](user/usage.md#mode-watch-folder).

---

## Quick start Desktop

L'application desktop JavaFX permet de déposer des fichiers, suivre les jobs et gérer les doublons.

```bash
# Depuis la racine du dépôt
cd desktop-app
mvn -q -DskipTests package
mvn -q javafx:run
```

> L'application nécessite que la stack Docker soit lancée. Configurer l'URL de l'orchestrateur via l'onglet **Configuration** (défaut : `http://localhost:18083`).

---

## Documentation IA

Les rapports et analyses produits par l'IA sont organisés dans [`docs/ia/`](ia/README.md) :

- `docs/ia/rapports-execution/` — rapports d'implémentation de features
- `docs/ia/rapports-migration/` — rapports de migration
- `docs/ia/templates/` — template officiel de rapport IA

Politique complète : [`.github/instructions/reports-docs.instructions.md`](../.github/instructions/reports-docs.instructions.md)

---

## Liens rapides

| Ressource | Chemin |
|---|---|
| Installation | [docs/user/installation.md](user/installation.md) |
| Utilisation | [docs/user/usage.md](user/usage.md) |
| Résolution de problèmes | [docs/user/troubleshooting.md](user/troubleshooting.md) |
| Setup développeur | [docs/dev/setup.md](dev/setup.md) |
| Tests | [docs/dev/testing.md](dev/testing.md) |
| Opérations & observabilité | [docs/dev/operations.md](dev/operations.md) |
| Contribution | [docs/dev/contributing.md](dev/contributing.md) |
| README racine | [README.md](../README.md) |

