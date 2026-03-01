# Runbook opérateur — comic2pdf-app

Ce runbook décrit **quoi faire** en cas d'incident backend (crash, job bloqué, saturation disque, état corrompu).

Pour les détails d'**observabilité** (comment lire les endpoints, formats JSON, logs), voir [operations.md](operations.md).

---

## Objectif et périmètre

Ce guide s'adresse aux opérateurs backend gérant la stack Docker `comic2pdf-app` en production.

**Couverture** :
- Diagnostic rapide via endpoints HTTP
- Procédures d'incident (6 cas courants)
- Actions manuelles contrôlées
- Escalade et collecte d'infos

**Hors périmètre** :
- Installation initiale → voir [`docs/user/installation.md`](../user/installation.md)
- Configuration des services → voir [`setup.md`](setup.md)
- Détails des endpoints → voir [`operations.md`](operations.md)

---

## Glossaire minimal

| Terme | Description |
|---|---|
| **jobKey** | Identifiant unique : `<fileHash>__<profileHash>` (2 SHA-256 séparés par `__`) |
| **stage** | Étape courante : `PREP` (extraction) ou `OCR` (reconnaissance texte) |
| **attemptPrep** / **attemptOcr** | Numéro de tentative (1, 2, 3) — max = `MAX_ATTEMPTS_PREP` / `MAX_ATTEMPTS_OCR` (défaut : 3) |
| **heartbeat** | Fichier `prep.heartbeat` ou `ocr.heartbeat` mis à jour par les workers toutes les ~5 secondes |
| **timeout** | Délai `JOB_TIMEOUT_SECONDS` (défaut : 600s = 10 min) avant de considérer un job stale |
| **state.json** | Fichier d'état d'un job dans `data/work/<jobKey>/state.json` |
| **index** | Fichier `data/index/jobs.json` — source de vérité de tous les jobs connus |

---

## Machine d'états (référence)

### États principaux

```
DISCOVERED → PREP_SUBMITTED → PREP_RUNNING → PREP_DONE
                                     ↓
                               PREP_RETRY (si échec)
                                     ↓
                            ERROR_PREP (si max attempts atteint)

PREP_DONE → OCR_SUBMITTED → OCR_RUNNING → DONE
                                   ↓
                             OCR_RETRY (si échec)
                                   ↓
                          ERROR_OCR (si max attempts atteint)
```

### États d'erreur et retry

| État | Cause | Transition suivante |
|---|---|---|
| `PREP_TIMEOUT` | Heartbeat stale (> `JOB_TIMEOUT_SECONDS`) | → `PREP_RETRY` |
| `PREP_ERROR` | Erreur worker (crash, outil absent) | → `PREP_RETRY` |
| `PREP_RETRY` | Retry planifié | → `PREP_RUNNING` (tentative suivante) |
| `ERROR_PREP` | `attemptPrep >= MAX_ATTEMPTS_PREP` | État final — fichier vers `data/error/` |
| `OCR_TIMEOUT` | Heartbeat stale (> `JOB_TIMEOUT_SECONDS`) | → `OCR_RETRY` |
| `OCR_ERROR` | Erreur worker ou PDF invalide | → `OCR_RETRY` |
| `OCR_RETRY` | Retry planifié | → `OCR_RUNNING` (tentative suivante) |
| `ERROR_OCR` | `attemptOcr >= MAX_ATTEMPTS_OCR` | État final — fichier vers `data/error/` |
| `DUPLICATE_PENDING` | Doublon détecté | Attend `decision.json` de l'app desktop |

### États anormaux (nécessitent intervention)

- Job en `PREP_RUNNING` ou `OCR_RUNNING` depuis > `2 × JOB_TIMEOUT_SECONDS` sans heartbeat récent
- Job en `*_RETRY` avec nombre de tentatives incohérent (attemptPrep ou attemptOcr > 3)
- `state.json` absent ou corrompu pour un job présent dans l'index

---

## Diagnostic rapide

### 1. Lire les métriques

**Commande** :

```powershell
# Windows PowerShell
Invoke-RestMethod http://localhost:18083/metrics
```

```bash
# Linux / macOS
curl http://localhost:18083/metrics
```

**Indicateurs clés** :

| Compteur | Seuil alerte | Action |
|---|---|---|
| `disk_error` | > 0 | Libérer espace disque (voir procédure 2) |
| `pdf_invalid` | > 5% des jobs | Vérifier logs OCR (voir procédure 3) |
| `input_rejected_size` | > 0 | Augmenter `MAX_INPUT_SIZE_MB` si légitime |
| `input_rejected_signature` | > 0 | Vérifier intégrité fichiers sources |
| `running` | > `MAX_JOBS_IN_FLIGHT` | Anomalie — investiguer jobs bloqués |
| `error` | Augmentation continue | Lire `data/error/` + logs |

### 2. Lister les jobs en cours

**Voir** : [operations.md — `GET /jobs`](operations.md#get-jobs)

```powershell
Invoke-RestMethod http://localhost:18083/jobs | Where-Object { $_.state -match 'RUNNING' }
```

### 3. Détail d'un job spécifique

**Voir** : [operations.md — `GET /jobs/{jobKey}`](operations.md#get-jobsjobkey)

```powershell
$jobKey = "a1b2c3d4e5f6__0011223344556677"
Invoke-RestMethod "http://localhost:18083/jobs/$jobKey"
```

**Champs critiques** :

| Champ | À vérifier |
|---|---|
| `state` | Cohérent avec `stage` et `attempt` ? |
| `attemptPrep` / `attemptOcr` | ≤ 3 (max configuré) ? |
| `updatedAt` | Récent (< 10 min) pour jobs RUNNING ? |
| `rawPdf` / `finalPdf` | Chemins existent sur disque ? |

---

## Procédures d'incident

### Procédure 1 — Job bloqué / heartbeat stale

**Symptômes** :
- Job en `PREP_RUNNING` ou `OCR_RUNNING` depuis > 10 minutes
- Métrique `running` stable (n'évolue pas)
- `GET /jobs/{jobKey}` montre `updatedAt` ancien

**Hypothèses** :
- Worker crashé ou surchargé
- Heartbeat non écrit (erreur I/O)

**Actions** :

1. **Vérifier le heartbeat sur disque** :

   ```powershell
   # Windows PowerShell
   $jobKey = "a1b2c3d4e5f6__0011223344556677"
   Get-Item ".\data\work\$jobKey\prep.heartbeat" | Select-Object LastWriteTime
   # OU pour OCR :
   Get-Item ".\data\work\$jobKey\ocr.heartbeat" | Select-Object LastWriteTime
   ```

   Si `LastWriteTime` > `JOB_TIMEOUT_SECONDS` (défaut 600s = 10 min) → heartbeat stale confirmé.

2. **Lire les logs du service concerné** :

   ```powershell
   # PREP bloqué
   docker compose logs prep-service --tail=50

   # OCR bloqué
   docker compose logs ocr-service --tail=50
   ```

   Chercher : `ERROR`, `Traceback`, `killed`, `OOMKilled`.

3. **Redémarrer le service bloqué** :

   ```powershell
   # Redémarrer prep-service
   docker compose restart prep-service

   # Redémarrer ocr-service
   docker compose restart ocr-service
   ```

   L'orchestrateur détectera automatiquement le heartbeat stale et basculera le job en `*_RETRY` au prochain tick.

4. **Augmenter le timeout si fichiers légitimement volumineux** :

   ```powershell
   # Via l'app desktop (onglet Configuration) OU :
   curl -X POST http://localhost:18083/config `
     -H "Content-Type: application/json" `
     -d '{"job_timeout_s": 1200}'
   ```

**Résultat attendu** : Job repris en `*_RETRY`, puis `*_RUNNING` (tentative suivante).

---

### Procédure 2 — Saturation disque (`disk_error`)

**Symptômes** :
- Métrique `disk_error` > 0
- Jobs rejetés immédiatement après découverte
- Fichiers sources déplacés vers `data/error/`

**Hypothèses** :
- Espace disque libre < `taille_fichier × DISK_FREE_FACTOR` (défaut 2.0)
- Accumulation de workdirs anciens

**Actions** :

1. **Vérifier l'espace disque disponible** :

   ```powershell
   # Windows PowerShell
   Get-PSDrive | Where-Object { $_.Name -eq 'C' } | Select-Object Free,Used
   ```

   ```bash
   # Linux / macOS
   df -h .
   ```

2. **Nettoyer les workdirs anciens manuellement** :

   ```powershell
   # Windows PowerShell — supprimer workdirs > 7 jours
   $days = 7
   Get-ChildItem ".\data\work\" -Directory |
     Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$days) } |
     Remove-Item -Recurse -Force -Verbose
   ```

   ```bash
   # Linux / macOS
   find ./data/work/ -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
   ```

3. **Vider `data/archive/` si nécessaire** :

   ```powershell
   # Déplacer les archives vers un stockage externe
   Move-Item ".\data\archive\*" "D:\backup-bd\" -Force
   ```

4. **Réduire `DISK_FREE_FACTOR` (déconseillé en production)** :

   ```yaml
   # docker-compose.yml
   environment:
     DISK_FREE_FACTOR: "1.5"
   ```

   Puis :

   ```powershell
   docker compose up -d
   ```

5. **Relancer les fichiers rejetés** :

   ```powershell
   # Déplacer de error/ vers in/ avec convention .part
   Get-ChildItem ".\data\error\" -Filter "*.cbz" | ForEach-Object {
     Copy-Item $_.FullName ".\data\in\$($_.Name).part"
     Rename-Item ".\data\in\$($_.Name).part" $_.Name
   }
   ```

**Résultat attendu** : Métrique `disk_error` stable, jobs traités normalement.

---

### Procédure 3 — PDF final invalide (`pdf_invalid`)

**Symptômes** :
- Métrique `pdf_invalid` > 0
- Jobs en boucle `OCR_RETRY` → `OCR_RUNNING` → `OCR_RETRY`
- Logs orchestrateur : `"PDF final invalide"`, `"message": "pdf_invalid"`

**Hypothèses** :
- PDF produit par `ocrmypdf` sans header `%PDF-`
- PDF trop petit (< `MIN_PDF_SIZE_BYTES`, défaut 1024 octets)
- Fichier source corrompu

**Actions** :

1. **Lire les logs OCR du job concerné** :

   ```powershell
   docker compose logs ocr-service --tail=100 | Select-String "jobKey"
   ```

   Chercher : `ocrmypdf`, `error`, `PriorOcrFoundError`, `EncryptedPdfError`.

2. **Vérifier le PDF produit manuellement** :

   ```powershell
   $jobKey = "a1b2c3d4e5f6__0011223344556677"
   $pdfPath = ".\data\work\$jobKey\final.pdf"
   
   # Vérifier existence
   Test-Path $pdfPath
   
   # Vérifier taille
   (Get-Item $pdfPath).Length
   
   # Vérifier header (premiers 5 octets)
   $bytes = [System.IO.File]::ReadAllBytes($pdfPath)[0..4]
   [System.Text.Encoding]::ASCII.GetString($bytes)
   # Attendu : "%PDF-"
   ```

3. **Tester le fichier source dans un lecteur BD** :

   Ouvrir le `.cbz`/`.cbr` source dans un lecteur (CDisplayEx, YACReader, etc.) pour vérifier qu'il n'est pas corrompu.

4. **Réduire `MIN_PDF_SIZE_BYTES` si fichiers légitimement petits** :

   ```yaml
   # docker-compose.yml
   environment:
     MIN_PDF_SIZE_BYTES: "512"
   ```

   Puis :

   ```powershell
   docker compose up -d
   ```

5. **Si le fichier source est corrompu** :

   Supprimer le job de l'index et déplacer le fichier source :

   ```powershell
   $jobKey = "a1b2c3d4e5f6__0011223344556677"
   
   # Supprimer workdir
   Remove-Item ".\data\work\$jobKey" -Recurse -Force
   
   # Supprimer de l'index (éditer jobs.json manuellement ou via script)
   ```

**Résultat attendu** : Jobs OCR réussis, métrique `pdf_invalid` stable.

---

### Procédure 4 — Fichier rejeté : taille ou signature invalide

**Symptômes** :
- Métrique `input_rejected_size` ou `input_rejected_signature` > 0
- Fichiers sources dans `data/error/` sans traitement

**Hypothèses** :
- Fichier > `MAX_INPUT_SIZE_MB` (défaut 500 Mo)
- Signature magic bytes invalide (ni ZIP ni RAR)

**Actions** :

1. **Vérifier la taille du fichier rejeté** :

   ```powershell
   Get-ChildItem ".\data\error\" | Select-Object Name, @{N='MB';E={[math]::Round($_.Length/1MB,2)}}
   ```

2. **Si fichier > 500 Mo ET légitime** :

   Augmenter la limite :

   ```yaml
   # docker-compose.yml
   environment:
     MAX_INPUT_SIZE_MB: "1000"
   ```

   Puis redémarrer :

   ```powershell
   docker compose up -d
   ```

   Relancer le fichier :

   ```powershell
   $fichier = "MonComic.cbz"
   Copy-Item ".\data\error\$fichier" ".\data\in\$fichier.part"
   Rename-Item ".\data\in\$fichier.part" $fichier
   ```

3. **Si signature invalide** :

   Vérifier les magic bytes :

   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes(".\data\error\MonComic.cbz")[0..3]
   $bytes | ForEach-Object { "{0:X2}" -f $_ }
   # CBZ (ZIP) attendu : 50 4B 03 04
   # CBR (RAR) attendu : 52 61 72 21 (ou RAR5)
   ```

   Si le fichier est un ZIP renommé en `.cbr`, renommer en `.cbz` et relancer.

**Résultat attendu** : Fichiers acceptés, métriques `input_rejected_*` stables.

---

### Procédure 5 — state.json corrompu

**Symptômes** :
- Logs orchestrateur : `"state.json corrompu (décodage invalide)"`, `"json_corrupt"`
- Job présent dans l'index mais `GET /jobs/{jobKey}` retourne erreur ou données incohérentes

**Hypothèses** :
- Écriture interrompue (crash pendant `atomic_write_json`)
- Corruption disque

**Actions** :

1. **Localiser le state.json corrompu** :

   ```powershell
   $jobKey = "a1b2c3d4e5f6__0011223344556677"
   $statePath = ".\data\work\$jobKey\state.json"
   
   # Tenter de lire
   Get-Content $statePath
   ```

2. **Supprimer le state.json corrompu** :

   ```powershell
   Remove-Item $statePath -Force
   ```

   L'orchestrateur recréera un `state.json` minimal au prochain tick grâce à `safe_load_json()`.

3. **Si le problème persiste** :

   Supprimer le job de l'index manuellement :

   ```powershell
   # Éditer data/index/jobs.json et retirer l'entrée du jobKey
   # Puis redémarrer l'orchestrateur
   docker compose restart orchestrator
   ```

4. **Vérifier l'intégrité du disque** :

   ```powershell
   # Windows
   chkdsk /F
   ```

   ```bash
   # Linux
   fsck -n /dev/sdX
   ```

**Résultat attendu** : Job repris ou supprimé, pas de nouvelles corruptions.

---

### Procédure 6 — Pic d'erreurs OCR / Tesseract

**Symptômes** :
- Métrique `error` augmente rapidement
- Logs OCR : erreurs Tesseract répétées (`tesseract failed`, `Error in pixReadStream`)

**Hypothèses** :
- Tesseract surchargé (trop de jobs OCR en parallèle)
- Mémoire insuffisante (OOM)
- Images sources corrompues

**Actions** :

1. **Vérifier les ressources Docker** :

   ```powershell
   docker stats --no-stream
   ```

   Chercher : `MEM %` > 90%, conteneur `ocr-service`.

2. **Réduire `OCR_CONCURRENCY` à 1** :

   ```powershell
   curl -X POST http://localhost:18083/config `
     -H "Content-Type: application/json" `
     -d '{"ocr_concurrency": 1}'
   ```

3. **Augmenter la RAM allouée à Docker Desktop** :

   Settings → Resources → Memory : minimum 4 Go (2 Go par job OCR + OS).

4. **Lire les logs OCR pour identifier le fichier problématique** :

   ```powershell
   docker compose logs ocr-service --tail=200 | Select-String "Error"
   ```

   Si un jobKey revient systématiquement, déplacer le fichier source vers `data/error/` manuellement.

**Résultat attendu** : Erreurs OCR stabilisées, jobs traités normalement.

---

## Actions manuelles contrôlées

### Déplacer un fichier de `/error` vers `/in`

**Convention atomique obligatoire** (ignorer les `.part`) :

```powershell
# Windows PowerShell
$fichier = "MonComic.cbz"
Copy-Item ".\data\error\$fichier" ".\data\in\$fichier.part"
Rename-Item ".\data\in\$fichier.part" $fichier
```

```bash
# Linux / macOS
cp ./data/error/MonComic.cbz ./data/in/MonComic.cbz.part
mv ./data/in/MonComic.cbz.part ./data/in/MonComic.cbz
```

### Supprimer un workdir manuellement

**Quand autoriser** :
- Job en état final (`DONE` ou `ERROR*`)
- Workdir > `KEEP_WORK_DIR_DAYS` jours (défaut 7)
- Job **absent** de `running` dans `/metrics`

**Commande** :

```powershell
$jobKey = "a1b2c3d4e5f6__0011223344556677"
Remove-Item ".\data\work\$jobKey" -Recurse -Force
```

**⚠️ Ne jamais supprimer un workdir pour un job en `*_RUNNING`** — risque de corruption.

### Augmenter JOB_TIMEOUT_SECONDS

**Quand** : Fichiers très volumineux (200+ pages) légitimement lents.

**Commande** :

```powershell
# Via app desktop (onglet Configuration) OU :
curl -X POST http://localhost:18083/config `
  -H "Content-Type: application/json" `
  -d '{"job_timeout_s": 1200}'
```

### Baisser OCR_CONCURRENCY

**Quand** : Surcharge CPU/mémoire, ralentissements généraux.

**Commande** :

```powershell
curl -X POST http://localhost:18083/config `
  -H "Content-Type: application/json" `
  -d '{"ocr_concurrency": 1}'
```

### Archiver et repartir

**Quand** : Accumulation de jobs en erreur, besoin de "reset propre".

**Commande** :

```powershell
# Arrêter la stack
docker compose down

# Archiver les données actuelles
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Compress-Archive -Path ".\data\*" -DestinationPath ".\backup-$timestamp.zip"

# Nettoyer (conserver uniquement in/ et out/)
Remove-Item ".\data\work\*" -Recurse -Force
Remove-Item ".\data\error\*" -Recurse -Force
Remove-Item ".\data\archive\*" -Recurse -Force
Remove-Item ".\data\index\*" -Force

# Redémarrer
docker compose up -d
```

---

## Escalade / Collecte d'infos

### Quels fichiers collecter pour un rapport d'incident

1. **Métriques** : `data/index/metrics.json`
2. **Index** : `data/index/jobs.json`
3. **state.json du job problématique** : `data/work/<jobKey>/state.json`
4. **Logs des 3 services** :
   - `data/logs/orchestrator.log`
   - `data/logs/prep-service.log`
   - `data/logs/ocr-service.log`
5. **Logs Docker** :

   ```powershell
   docker compose logs --tail=500 > logs-docker.txt
   ```

### Quelles métriques relever

- Sortie de `GET /metrics` (JSON complet)
- Sortie de `GET /jobs` (liste complète)
- `docker stats --no-stream` (utilisation CPU/RAM)
- Espace disque disponible (`df -h` ou `Get-PSDrive`)

### Où trouver state.json d'un job

```
data/work/<jobKey>/state.json
```

Si le job est en erreur finale :

```
data/error/<jobKey>/state.json
```

### Comment joindre un rapport d'incident

1. Créer une archive contenant les fichiers ci-dessus.
2. Ouvrir une issue GitHub avec label `incident` + `backend`.
3. Joindre l'archive + description (symptômes, actions tentées, résultats).
4. Taguer `@team-architecture`.

---

## Logs persistants

**Emplacement** : `data/logs/`

```
data/logs/
├── orchestrator.log       # log courant
├── orchestrator.log.1     # backup 1 (le plus récent)
├── orchestrator.log.2     # backup 2
├── prep-service.log
├── prep-service.log.1
├── ocr-service.log
└── ocr-service.log.1
```

**Activer le format JSON** (pour parsing automatisé) :

```yaml
# docker-compose.yml
environment:
  LOG_JSON: "true"
```

**Analyser les logs** :

Voir [operations.md — Logs JSON structurés](operations.md#logs-json-structurés) pour les commandes de filtrage.

---

## Voir aussi

| Document | Description |
|---|---|
| [operations.md](operations.md) | Observabilité HTTP — endpoints, formats JSON, logs, dimensionnement |
| [setup.md](setup.md) | Variables d'environnement complètes, ports, configuration |
| [troubleshooting.md](../user/troubleshooting.md) | Guide utilisateur — problèmes courants (fichier non traité, doublons, etc.) |

---

## Retour

[← Retour à la documentation développeur](README.md)

