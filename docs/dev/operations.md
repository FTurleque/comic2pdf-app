# Opérations & Observabilité — comic2pdf-app

Ce guide couvre les endpoints HTTP de l'orchestrateur, les formats de données, les logs structurés et les bonnes pratiques de dimensionnement.

---

## Endpoints d'observabilité (HTTP orchestrateur)

L'orchestrateur expose un serveur HTTP minimal (stdlib Python `http.server`) sur le port `8080` (exposé en `18083` via Docker).

### `GET /metrics`

Retourne les métriques courantes du pipeline.

```powershell
# Windows PowerShell
Invoke-RestMethod http://localhost:18083/metrics
```

```bash
# Linux / macOS
curl http://localhost:18083/metrics
```

**Réponse (exemple type)** :

```json
{
  "done": 42,
  "error": 2,
  "running": 1,
  "queued": 3,
  "disk_error": 0,
  "pdf_invalid": 1,
  "input_rejected_size": 0,
  "input_rejected_signature": 1,
  "updatedAt": "2026-02-28T10:15:00Z"
}
```

| Compteur | Description |
|---|---|
| `done` | Jobs terminés avec succès (état `DONE`) |
| `error` | Jobs en erreur définitive (état `ERROR*`) |
| `running` | Jobs actuellement en cours de traitement |
| `queued` | Jobs découverts mais pas encore soumis |
| `disk_error` | Rejets pour espace disque insuffisant |
| `pdf_invalid` | PDFs finaux invalides détectés (header ou taille) |
| `input_rejected_size` | Fichiers rejetés car trop volumineux (> MAX_INPUT_SIZE_MB) |
| `input_rejected_signature` | Fichiers rejetés car signature magic bytes invalide |
| `updatedAt` | Horodatage ISO 8601 de la dernière mise à jour |

---

### `GET /jobs`

Retourne la liste de tous les jobs connus de l'index.

```powershell
Invoke-RestMethod http://localhost:18083/jobs
```

```bash
curl http://localhost:18083/jobs
```

**Réponse (exemple type)** :

```json
[
  {
    "jobKey": "a1b2c3d4e5f6__0011223344556677",
    "inputFile": "MonComic.cbz",
    "state": "DONE",
    "stage": "OCR",
    "attempt": 1,
    "updatedAt": "2026-02-28T10:05:00Z"
  },
  {
    "jobKey": "f9e8d7c6b5a4__aabbccddeeff0011",
    "inputFile": "AutreComic.cbr",
    "state": "OCR_RUNNING",
    "stage": "OCR",
    "attempt": 1,
    "updatedAt": "2026-02-28T10:14:55Z"
  }
]
```

---

### `GET /jobs/{jobKey}`

Retourne le détail d'un job spécifique (contenu du `state.json`). Retourne `404` si le jobKey est inconnu.

```powershell
Invoke-RestMethod "http://localhost:18083/jobs/a1b2c3d4e5f6__0011223344556677"
```

```bash
curl "http://localhost:18083/jobs/a1b2c3d4e5f6__0011223344556677"
```

**Réponse 200 (exemple type)** :

```json
{
  "jobKey": "a1b2c3d4e5f6__0011223344556677",
  "inputFile": "MonComic.cbz",
  "state": "DONE",
  "stage": "OCR",
  "attempt": 1,
  "workDir": "/data/work/a1b2c3d4e5f6__0011223344556677",
  "rawPdf": "/data/work/a1b2c3d4e5f6__0011223344556677/raw.pdf",
  "finalPdf": "/data/out/MonComic__job-a1b2c3d4e5f6__0011223344556677.pdf",
  "createdAt": "2026-02-28T10:00:00Z",
  "updatedAt": "2026-02-28T10:05:00Z"
}
```

**Réponse 404** :

```json
{"error": "job not found"}
```

---

### `GET /config`

Retourne la configuration runtime actuelle de l'orchestrateur.

```powershell
Invoke-RestMethod http://localhost:18083/config
```

```bash
curl http://localhost:18083/config
```

**Réponse (exemple type)** :

```json
{
  "prep_concurrency": 2,
  "ocr_concurrency": 1,
  "job_timeout_s": 600,
  "default_ocr_lang": "fra+eng"
}
```

---

### `POST /config`

Met à jour à chaud une ou plusieurs clés de configuration autorisées.

**Clés autorisées** : `prep_concurrency`, `ocr_concurrency`, `job_timeout_s`, `default_ocr_lang`

```powershell
# Windows PowerShell
$body = @{ prep_concurrency = 3; ocr_concurrency = 2; job_timeout_s = 900 } | ConvertTo-Json
Invoke-RestMethod http://localhost:18083/config -Method POST `
  -ContentType "application/json" -Body $body
```

```bash
# Linux / macOS
curl -X POST http://localhost:18083/config \
  -H "Content-Type: application/json" \
  -d '{"prep_concurrency": 3, "ocr_concurrency": 2, "job_timeout_s": 900}'
```

**Réponse 200** :

```json
{"status": "ok"}
```

> Les clés inconnues sont ignorées. Les valeurs invalides (type incorrect) retournent `400 Bad Request`.

---

### Endpoints FastAPI des services

#### prep-service (port `18081` en local)

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/info` | Versions des outils (7z, img2pdf) |
| `POST` | `/jobs/prep` | Soumettre un job PREP |
| `GET` | `/jobs/{id}` | État d'un job PREP |

#### ocr-service (port `18082` en local)

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/info` | Versions des outils (ocrmypdf, tesseract) |
| `POST` | `/jobs/ocr` | Soumettre un job OCR |
| `GET` | `/jobs/{id}` | État d'un job OCR |

---

## Format `metrics.json`

Le fichier `data/index/metrics.json` est persisté à chaque tick de l'orchestrateur.

```json
{
  "done": 42,
  "error": 2,
  "running": 1,
  "queued": 3,
  "disk_error": 0,
  "pdf_invalid": 1,
  "input_rejected_size": 0,
  "input_rejected_signature": 1,
  "updatedAt": "2026-02-28T10:15:00Z"
}
```

---

## Format `state.json` d'un job

Chaque job dispose d'un fichier `data/work/<jobKey>/state.json` (ou `data/error/<jobKey>/state.json` si en erreur).

```json
{
  "jobKey": "a1b2c3d4e5f6__0011223344556677",
  "inputFile": "MonComic.cbz",
  "state": "DONE",
  "stage": "OCR",
  "attempt": 1,
  "prepAttempts": 1,
  "ocrAttempts": 1,
  "workDir": "/data/work/a1b2c3d4e5f6__0011223344556677",
  "rawPdf": "/data/work/a1b2c3d4e5f6__0011223344556677/raw.pdf",
  "finalPdf": "/data/out/MonComic__job-a1b2c3d4e5f6__0011223344556677.pdf",
  "profile": {
    "ocrLang": "fra+eng",
    "toolVersions": {
      "7z": "21.07",
      "img2pdf": "0.5.1",
      "ocrmypdf": "15.4.2",
      "tesseract": "5.3.0"
    }
  },
  "createdAt": "2026-02-28T10:00:00Z",
  "updatedAt": "2026-02-28T10:05:00Z"
}
```

---

## Logs JSON structurés

### Activation

```yaml
# docker-compose.yml — ajouter pour chaque service concerné
environment:
  LOG_JSON: "true"
```

### Format d'une ligne de log JSON

```json
{
  "timestamp": "2026-02-28T10:05:42Z",
  "level": "INFO",
  "service": "orchestrator",
  "message": "Job traité avec succès",
  "jobKey": "a1b2c3d4e5f6__0011223344556677",
  "stage": "OCR",
  "attempt": 1
}
```

| Champ | Obligatoire | Description |
|---|---|---|
| `timestamp` | Oui | Horodatage ISO 8601 UTC |
| `level` | Oui | Niveau de log : `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `service` | Oui | Nom du service émetteur |
| `message` | Oui | Message de log lisible |
| `jobKey` | Non | Présent si le log concerne un job spécifique |
| `stage` | Non | `PREP` ou `OCR` si pertinent |
| `attempt` | Non | Numéro de tentative (1, 2, 3) si pertinent |

### Analyser les logs JSON

```powershell
# Windows PowerShell — filtrer les erreurs
docker compose logs orchestrator 2>&1 | ForEach-Object {
    try {
        $j = $_ | ConvertFrom-Json
        if ($j.level -eq "ERROR") { $_ | ConvertFrom-Json | Format-Table }
    } catch {}
}
```

```bash
# Linux / macOS avec jq
docker compose logs orchestrator 2>&1 | grep '^{' | jq 'select(.level == "ERROR")'

# Tous les logs d'un job spécifique
docker compose logs orchestrator 2>&1 | grep '^{' | \
  jq 'select(.jobKey == "a1b2c3d4e5f6__0011223344556677")'
```

---

## Janitor workdir

L'orchestrateur exécute un nettoyage périodique des workdirs toutes les **600 secondes**.

### Comportement

| Valeur `KEEP_WORK_DIR_DAYS` | Comportement |
|---|---|
| `7` (défaut) | Supprime les workdirs de plus de 7 jours |
| `0` | Supprime le workdir immédiatement après que le job passe en état `DONE` |
| `30` | Conserve les workdirs 30 jours (utile pour débogage) |

> Le janitor ne supprime que les dossiers dans `data/work/`. Les dossiers dans `data/error/` ne sont jamais supprimés automatiquement.

### Nettoyage manuel

```powershell
# Windows PowerShell — supprimer les workdirs de plus de N jours
$days = 7
Get-ChildItem ".\data\work\" -Directory |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$days) } |
  Remove-Item -Recurse -Force -Verbose
```

```bash
# Linux / macOS
find ./data/work/ -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
```

---

## Bonnes pratiques de dimensionnement

### CPU

| Ressource | Recommandation |
|---|---|
| OCR (Tesseract) | 2–4 cœurs par job OCR concurrent |
| PREP (7z + img2pdf) | 1–2 cœurs par job PREP concurrent |
| Orchestrateur | < 0.5 cœur (I/O-bound) |

Exemple : machine 8 cœurs → `OCR_CONCURRENCY=2`, `PREP_CONCURRENCY=3`.

### Mémoire RAM

| Service | Minimum | Recommandé |
|---|---|---|
| prep-service | 256 Mo | 512 Mo |
| ocr-service (Tesseract) | 1 Go | 2 Go par job concurrent |
| orchestrator | 128 Mo | 256 Mo |
| desktop-app (JavaFX) | 256 Mo | 512 Mo |

### Stockage — règle `DISK_FREE_FACTOR`

Avant chaque étape PREP, l'orchestrateur vérifie :

```
espace_libre_requis = taille_fichier_entrant × DISK_FREE_FACTOR (défaut : 2.0)
```

**Exemple** : un fichier `.cbz` de 200 Mo nécessite 400 Mo d'espace libre.

Prévoir suffisamment d'espace pour :
- Le fichier source × `DISK_FREE_FACTOR` (pendant le traitement)
- Le PDF final (généralement plus petit que la source)
- Les workdirs retenus (× `KEEP_WORK_DIR_DAYS`)

### Recommandation générale

Pour un usage courant (fichiers de 50–200 Mo, traitement de 10–50 fichiers/jour) :
- CPU : 4 cœurs minimum
- RAM : 4 Go minimum (2 Go pour Tesseract + OS + autres services)
- Stockage : 10× la taille totale du corpus source

---

## Retour

[← Retour à la documentation développeur](README.md)

