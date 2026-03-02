# RAPPORT_IMPLEMENTATION_2026-03-02

**Généré par IA** · Outil : GitHub Copilot

---

## 1. Informations générales

| Champ | Valeur |
|---|---|
| **Type** | IMPLEMENTATION |
| **Date** | 2026-03-02 |
| **Auteur / équipe** | GitHub Copilot (soumission : équipe comic2pdf-app) |
| **PR liée** | À renseigner lors de la soumission |
| **Issue liée** | À renseigner |

---

## 2. Contexte et résumé

Implémentation complète de 5 commits sur `FTurleque/comic2pdf-app` couvrant trois axes : UI desktop enrichie, sécurité renforcée (API key + zip-slip + Docker non-root), et tests + CI GitHub Actions. Aucune régression sur le pipeline existant (backward-compatible). L'objectif est d'industrialiser la qualité du projet sans modifier son architecture file-based ni son API (seul `POST /config` est maintenant protégé).

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `desktop-app/src/main/java/com/comic2pdf/desktop/config/AppConfig.java` | Modifié | Ajout du champ `apiKey` (nullable, défaut vide), getter/setter. Non inclus dans `toOrchPayload()`. |
| `desktop-app/src/main/java/com/comic2pdf/desktop/config/ConfigService.java` | Modifié | Résolution clé API : env var `ORCHESTRATOR_API_KEY` prioritaire sur config.json. Chemin Unix XDG_CONFIG_HOME. Permissions POSIX 600 best-effort. |
| `desktop-app/src/main/java/com/comic2pdf/desktop/client/OrchestratorClient.java` | Modifié | Ajout de `setApiKey()`/`hasApiKey()`, injection header `X-Api-Key` sur toutes les requêtes. Enrichissement de `parseJobRow()` avec `outPdf` et `errorMessage`. |
| `desktop-app/src/main/java/com/comic2pdf/desktop/service/AppServices.java` | Modifié | Dans `createDefault()` : chargement config puis injection clé API dans le client. |
| `desktop-app/src/main/java/com/comic2pdf/desktop/model/JobRow.java` | Modifié | Ajout de `outPdf` et `errorMessage` (StringProperty), constructeur enrichi, `updateFrom()` étendu. |
| `desktop-app/src/main/resources/fxml/ConfigView.fxml` | Modifié | Ajout d'un `PasswordField apiKeyField` et d'un `Label apiKeySourceLabel`. |
| `desktop-app/src/main/java/com/comic2pdf/desktop/ui/controller/ConfigController.java` | Modifié | Gestion du champ clé API (env var → désactivé + indication de source). |
| `desktop-app/src/main/java/com/comic2pdf/desktop/ui/controller/JobsController.java` | Modifié | Filtres (recherche + ComboBox état), panneau détail, bannière offline + backoff exponentiel, actions copier/ouvrir. |
| `desktop-app/src/main/resources/fxml/JobsView.fxml` | Modifié | SplitPane avec panneau détail, barre recherche/filtres, bannière offline, boutons d'action. |
| `desktop-app/src/main/java/com/comic2pdf/desktop/util/FxUtils.java` | Modifié | Ajout de `openFile(Path)`. |
| `desktop-app/pom.xml` | Modifié | Ajout du plugin JaCoCo 0.8.12 (prepare-agent + report). |
| `services/orchestrator/app/http_server.py` | Modifié | Auth `POST /config` via `X-Api-Key` + `hmac.compare_digest`. Fallback localhost si pas de clé. Audit logs IP. |
| `services/orchestrator/app/utils.py` | Modifié | Ajout de `safe_path()` (protection path traversal). |
| `services/orchestrator/Dockerfile` | Modifié | Utilisateur non-root `appuser` en runtime. |
| `services/prep-service/app/core.py` | Modifié | Ajout de `ZipSlipError` et `check_zip_slip()`, intégré dans `list_and_sort_images()`. |
| `services/prep-service/app/main.py` | Modifié | Catch `ZipSlipError` dans `run_job()` : cleanup workdir + état ERROR. |
| `services/prep-service/Dockerfile` | Modifié | Utilisateur non-root `appuser` en runtime. |
| `services/ocr-service/Dockerfile` | Modifié | Utilisateur non-root `appuser` en runtime. |
| `services/orchestrator/requirements-dev.txt` | Modifié | Ajout de `pip-audit` et `httpx`. |
| `services/prep-service/requirements-dev.txt` | Modifié | Ajout de `pip-audit`. |
| `services/ocr-service/requirements-dev.txt` | Modifié | Ajout de `pip-audit`. |
| `README.md` | Modifié | Section sécurité (ORCHESTRATOR_API_KEY, config.json, zip-slip), section CI GitHub Actions. |

### Fichiers nouveaux

| Fichier | Description |
|---|---|
| `desktop-app/src/test/java/.../config/ConfigServiceTest.java` | Tests enrichis : apiKey persistée, apiKey absente du payload, compatibility JSON ancien. |
| `desktop-app/src/test/java/.../client/OrchestratorClientTest.java` | Tests header X-Api-Key (GET/POST), HTTP 401/403, parsing JSON enrichi. |
| `services/orchestrator/tests/test_auth.py` | Tests auth POST /config : bonne clé (200), mauvaise clé (401), localhost sans clé (200), IP externe (403), audit logs. |
| `services/orchestrator/tests/test_safe_path.py` | Tests safe_path : traversal ../../ (ValueError), chemin valide, chemin absolu externe. |
| `services/prep-service/tests/test_security.py` | Tests zip-slip : check_zip_slip, list_and_sort_images via mock, run_job → ERROR + cleanup. |
| `.github/workflows/ci.yml` | CI principale : python-tests + coverage, python-audit (pip-audit), java-tests (JaCoCo), java-audit (OWASP). |
| `.github/workflows/e2e.yml` | E2E Docker sur workflow_dispatch ou label run-e2e. |
| `tests/e2e/make_test_cbz.py` | Générateur de CBZ minimal (Pillow ou fallback PNG synthétique). |
| `tests/e2e/test_pipeline_e2e.py` | Script E2E : dépôt CBZ → attente PDF → vérification header %PDF-. |

### Variables d'environnement ajoutées

| Variable | Service | Défaut | Description |
|---|---|---|---|
| `ORCHESTRATOR_API_KEY` | orchestrator + desktop-app | *(absent = pas d'auth)* | Clé API pour protéger `POST /config`. |

### Endpoints HTTP modifiés

| Méthode | Route | Changement |
|---|---|---|
| `POST` | `/config` | Protégé par `X-Api-Key`. Clé absente + non-localhost → 403. Mauvaise clé → 401. |
| `GET` | tous | Inchangés (sans authentification). |

---

## 4. Étapes pour reproduire / commandes exécutées

### Tests unitaires Python

```powershell
# prep-service
cd services\prep-service
python -m pytest tests/test_security.py tests/test_core.py -q

# orchestrator
cd ..\orchestrator
python -m pytest tests/test_auth.py tests/test_safe_path.py tests/test_http_server.py -q
```

```bash
# Linux/macOS
cd services/prep-service && pytest tests/test_security.py tests/test_core.py -q
cd ../orchestrator && pytest tests/test_auth.py tests/test_safe_path.py -q
```

### Tests Java

```powershell
cd desktop-app ; mvn test
```

### Script global

```powershell
.\run_tests.ps1
```

### Tests E2E (Docker requis)

```bash
docker compose up -d --build
python tests/e2e/test_pipeline_e2e.py
docker compose down
```

### Audit sécurité local

```bash
# Python
pip install pip-audit
pip-audit -r services/orchestrator/requirements.txt

# Java
cd desktop-app
mvn org.owasp:dependency-check-maven:check -DfailBuildOnCVSS=9
```

---

## 5. Notes de migration

1. **`ORCHESTRATOR_API_KEY`** : optionnelle. Sans elle, `POST /config` est restreint à localhost. Avec elle, le header `X-Api-Key` est requis.
2. **config.json desktop** : nouveau champ `apiKey` ajouté. Backward-compatible : les anciens fichiers sans ce champ sont chargés normalement (défaut = chaîne vide).
3. **Docker** : les 3 services tournent maintenant en utilisateur `appuser` (non-root). Le volume `data/` doit être accessible en lecture/écriture par cet utilisateur (les dossiers créés par Docker Compose avec UID 1000 conviennent dans la plupart des cas).

---

## 6. Liens vers PR / issues

- PR : À renseigner
- Issues : À renseigner

---

## 7. Contact pour questions

Ouvrir une issue dans le dépôt et taguer `@team-architecture`.

