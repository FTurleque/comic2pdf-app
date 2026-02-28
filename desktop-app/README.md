# Desktop App — Comic2PDF (JavaFX)

Interface graphique JavaFX pour déposer des fichiers, suivre les jobs et gérer les doublons.

> Prérequis : stack Docker démarrée (`docker compose up -d --build` depuis la racine).
> Java 21 + Maven 3.9+.

---

## Lancement rapide

```powershell
# Depuis la racine du dépôt
cd desktop-app

# Build sans tests (optionnel — inclus dans javafx:run)
mvn -q -DskipTests package

# Lancer l'interface
mvn -q javafx:run
```

### Variable d'environnement `ORCHESTRATOR_URL`

L'URL de l'orchestrateur peut être configurée via la variable d'environnement
`ORCHESTRATOR_URL` (défaut : `http://localhost:8080`) ou depuis l'onglet **Configuration**
de l'interface (persisté dans `%APPDATA%\comic2pdf\config.json`).

```powershell
# Exemple avec URL personnalisée
$env:ORCHESTRATOR_URL = "http://localhost:18083"
mvn -q javafx:run
```

Scripts dédiés disponibles dans [`scripts/`](../scripts/) :
- Windows : `scripts\run_desktop.ps1`
- Linux/macOS : `scripts/run_desktop.sh`

---

## Fonctionnalités

| Onglet | Rôle |
|---|---|
| **Doublons** | Affiche les fichiers en attente de décision (doublon détecté) |
| **Jobs** | Suivi temps-réel des jobs (refresh 3 s) — état, étape, tentatives |
| **Configuration** | URL orchestrateur, concurrences, timeout, langue OCR |

---

## Tests

```powershell
cd desktop-app
mvn test
```

Les tests `@Tag("ui")` sont **exclus** par défaut (nécessitent un affichage).

```powershell
# Tests UI headless (opt-in)
mvn -Pui-tests test -Dtestfx.headless=true -Dprism.order=sw
```

---

## License

Ce module fait partie du projet **Comic2PDF**, distribué sous **licence MIT** —
voir [`../LICENSE`](../LICENSE).

Les composants tiers (OpenJFX GPL-2.0+CE, Jackson Apache-2.0, JUnit 5 EPL-2.0,
TestFX, Ghostscript AGPL-3.0, etc.) ont leurs propres licences, listées dans
[`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

> ⚠️ **Ghostscript (AGPL-3.0)** : bien que Ghostscript ne soit pas une dépendance
> directe de ce module JavaFX, il est utilisé par le service `ocr-service` Docker.
> Sa licence peut imposer des obligations lors de la redistribution d'un binaire
> dérivé intégrant l'ensemble du pipeline — voir
> [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) pour le disclaimer complet.

