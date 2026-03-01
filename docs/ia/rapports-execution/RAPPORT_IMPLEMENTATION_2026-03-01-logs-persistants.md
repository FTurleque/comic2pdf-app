# RAPPORT_IMPLEMENTATION_2026-03-01-logs-persistants

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `Équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Logs persistants avec rotation (RotatingFileHandler) — 3 services Python |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-03-01` |
| **Auteur(s)** | Équipe comic2pdf-app |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | N/A |

---

## 2. Contexte et résumé

Les trois services Python (`orchestrator`, `prep-service`, `ocr-service`) ne loguaient que vers stdout.
Cette implémentation ajoute des logs persistants sur fichier avec rotation automatique via `logging.handlers.RotatingFileHandler` (stdlib Python — aucune dépendance externe ajoutée).
Le format JSON optionnel (variable `LOG_JSON`) est conservé et s'applique au handler fichier comme au handler stdout.
Des tests isolés (`importlib.reload` + `reset_logger_for_tests`) couvrent la création du fichier, la rotation et la validité JSON.

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Type | Description de la modification |
|---|---|---|
| `services/orchestrator/app/logger.py` | Modifié | Ajout `logging.handlers`, 5 nouvelles constantes env, `get_logger` avec `RotatingFileHandler` + `StreamHandler`, `reset_logger_for_tests` |
| `services/prep-service/app/logger.py` | Modifié | Même logique — service `prep-service`, fichier `prep-service.log` |
| `services/ocr-service/app/logger.py` | Modifié | Même logique — service `ocr-service`, fichier `ocr-service.log` |
| `docker-compose.yml` | Modifié | Ajout de `LOG_DIR=/data/logs` (+ variables commentées) pour les 3 services |
| `docs/dev/operations.md` | Modifié | Ajout d'une section « Logs persistants » avec tableau des variables, exemples d'analyse |

### Fichiers créés

| Fichier | Description |
|---|---|
| `services/orchestrator/tests/test_logger_persistence.py` | 12 tests : création fichier, rotation (.1, .2), JSON valide, champs obligatoires, idempotence, reset |
| `services/prep-service/tests/test_logger_persistence.py` | 6 tests : création, rotation, JSON, service name, reset |
| `services/ocr-service/tests/test_logger_persistence.py` | 6 tests : création, rotation, JSON, service name, reset |

### Variables d'environnement ajoutées

| Variable | Services | Défaut | Description |
|---|---|---|---|
| `LOG_DIR` | tous | `/data/logs` | Répertoire de stockage des fichiers de log |
| `LOG_FILE` | tous | `<service>.log` | Nom du fichier de log par service |
| `LOG_LEVEL` | tous | `INFO` | Niveau de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_ROTATE_MAX_BYTES` | tous | `10000000` | Taille max avant rotation (10 Mo) |
| `LOG_ROTATE_BACKUPS` | tous | `5` | Nombre de fichiers de sauvegarde conservés |

> `LOG_JSON` existait déjà — comportement inchangé, s'applique désormais aussi au handler fichier.

---

## 4. Étapes pour reproduire / commandes exécutées

```powershell
# orchestrator
cd services\orchestrator
.\.venv\Scripts\Activate.ps1
python -m pytest tests/test_logger_persistence.py -v

# prep-service
cd ..\prep-service
.\.venv\Scripts\Activate.ps1
python -m pytest tests/test_logger_persistence.py -v

# ocr-service
cd ..\ocr-service
.\.venv\Scripts\Activate.ps1
python -m pytest tests/test_logger_persistence.py -v
```

### Résultats des tests

| Module | Tests nouveaux | Tests total | Résultat |
|---|---|---|---|
| `orchestrator` | 12 | 95 | ✅ PASS |
| `prep-service` | 6 | 18 | ✅ PASS |
| `ocr-service` | 6 | 23 | ✅ PASS |

---

## 5. Points d'attention / Limitations

- Le dossier `data/` est dans `.gitignore` — les fichiers `*.log` sont aussi ignorés (règle `*.log` dans `.gitignore`) : **les logs ne sont jamais commités**, ce qui est le comportement attendu.
- En environnement Docker, `LOG_DIR=/data/logs` utilise le volume `./data:/data` déjà monté — aucun volume supplémentaire requis.
- Les tests utilisent `importlib.reload()` pour isoler les variables d'environnement ; le nom du logger dans chaque test est unique pour éviter les collisions de registre Python.
- La classe `_JsonFormatter` utilise `_SERVICE` comme variable de module — après `reload`, elle lit la valeur du module rechargé correctement.

---

## 6. Liens et références

- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`
- Documentation opérations : `docs/dev/operations.md` (section « Logs persistants »)

---

## 7. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

