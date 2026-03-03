# Guide rapide — Fonctionnalités de robustesse FS

Ce guide explique comment utiliser les fonctionnalités de robustesse du système de fichiers dans comic2pdf-app.

## Variables d'environnement

### Configuration de base

```bash
# Nettoyage des workdirs
KEEP_WORK_DIR_DAYS=7              # Jours avant suppression (défaut: 7)
                                   # 0 = suppression immédiate après DONE
                                   # 30 = conservation 30 jours (débogage)

# Validation PDF
MIN_PDF_SIZE_BYTES=1024            # Taille minimale PDF valide (défaut: 1024)

# Espace disque
DISK_FREE_FACTOR=2.0               # Espace requis = taille_fichier × facteur
                                   # (défaut: 2.0)

# Limitation taille fichiers entrants
MAX_INPUT_SIZE_MB=500              # Taille max fichiers .cbz/.cbr (défaut: 500)
```

### Exemple docker-compose.yml

```yaml
services:
  orchestrator:
    image: comic2pdf-orchestrator
    environment:
      # Nettoyage agressif pour environnement CI/test
      KEEP_WORK_DIR_DAYS: 0
      
      # Validation stricte des PDFs
      MIN_PDF_SIZE_BYTES: 2048
      
      # Sécurité espace disque (réservation 3× la taille du fichier)
      DISK_FREE_FACTOR: 3.0
      
      # Limite fichiers entrants à 200 Mo
      MAX_INPUT_SIZE_MB: 200
    volumes:
      - ./data:/data
```

## Métriques exposées

Les métriques suivantes sont disponibles via `GET http://orchestrator:8080/metrics` :

### Métriques de robustesse FS

| Métrique | Description |
|---|---|
| `disk_error` | Jobs rejetés pour espace disque insuffisant |
| `pdf_invalid` | Jobs avec PDF final invalide/corrompu |
| `input_rejected_size` | Fichiers entrants trop grands (> MAX_INPUT_SIZE_MB) |
| `input_rejected_signature` | Fichiers sans signature ZIP/RAR valide |

### Métriques de pipeline

| Métrique | Description |
|---|---|
| `done` | Jobs terminés avec succès |
| `error` | Jobs en erreur définitive (max tentatives atteint) |
| `running` | Jobs en cours de traitement |
| `queued` | Jobs en attente de traitement |

### Exemple de récupération

```powershell
# PowerShell
$metrics = Invoke-RestMethod http://localhost:8080/metrics
Write-Host "Erreurs disque : $($metrics.disk_error)"
Write-Host "PDFs invalides : $($metrics.pdf_invalid)"
```

```bash
# Linux / macOS avec jq
curl -s http://localhost:8080/metrics | jq '{disk_error, pdf_invalid, done, error}'
```

## Comportements du janitor workdir

Le janitor s'exécute **toutes les 600 secondes (10 minutes)**.

### Scénarios

#### 1. Conservation par défaut (7 jours)

```bash
KEEP_WORK_DIR_DAYS=7   # Défaut
```

- Les workdirs sont conservés 7 jours après la fin du job
- Utile pour le débogage post-mortem
- Le janitor supprime uniquement les dossiers > 7 jours

#### 2. Nettoyage immédiat (CI/test)

```bash
KEEP_WORK_DIR_DAYS=0
```

- Le workdir est supprimé **immédiatement** après que le job passe en `DONE`
- Pas d'attente du janitor
- Recommandé pour les environnements CI/test avec espace limité

#### 3. Conservation longue durée (débogage)

```bash
KEEP_WORK_DIR_DAYS=30
```

- Les workdirs sont conservés 30 jours
- Utile pour l'analyse forensique
- Nécessite plus d'espace disque

### Protection des jobs en cours

Le janitor **ne supprime jamais** :
- Les workdirs de jobs en cours (`running_job_keys`)
- Les dossiers système (préfixe `_`, ex: `_staging`)
- Les dossiers dans `data/error/` (jamais nettoyés automatiquement)

## Validation des PDFs

### Critères de validation

Un PDF est considéré **valide** si :
1. Le fichier existe
2. La taille ≥ `MIN_PDF_SIZE_BYTES` (défaut: 1024 octets)
3. Le header commence par `%PDF-`

### En cas d'échec

Si `validate_pdf()` retourne `False` :
1. Le job passe en état `OCR_RETRY`
2. La métrique `pdf_invalid` est incrémentée
3. Le fichier PDF invalide **n'est pas déplacé** vers `/out`
4. Le job est réessayé (jusqu'à `MAX_ATTEMPTS_OCR` fois)

### Exemple de logs

```json
{
  "level": "ERROR",
  "message": "PDF final invalide",
  "jobKey": "abc123__def456",
  "stage": "OCR_FINALIZE",
  "timestamp": "2026-03-03T14:30:00Z"
}
```

## Vérification espace disque

### Calcul

Avant chaque étape PREP :

```
espace_requis = taille_fichier_entrant × DISK_FREE_FACTOR
```

**Exemple** : 
- Fichier `.cbz` de 150 Mo
- `DISK_FREE_FACTOR=2.0`
- Espace requis = 300 Mo

### En cas d'espace insuffisant

1. Le job **n'est pas lancé**
2. Le fichier est déplacé vers `data/error/`
3. La métrique `disk_error` est incrémentée
4. Log ERROR avec détail

### Recommandations de dimensionnement

| Scénario | Taille moyenne fichiers | DISK_FREE_FACTOR | Espace disque recommandé |
|---|---|---|---|
| Usage léger | 50-100 Mo | 2.0 | 50 Go |
| Usage moyen | 100-200 Mo | 2.0 | 100 Go |
| Usage intensif | 200-500 Mo | 2.0 | 200 Go |
| CI/test (KEEP_WORK_DIR_DAYS=0) | Variable | 2.0 | 10 Go |

**Formule** :
```
Espace total = (taille_corpus × DISK_FREE_FACTOR) + (PDFs générés × 1.5) + (workdirs conservés × KEEP_WORK_DIR_DAYS)
```

## Validation taille/signature fichiers entrants

### Vérification de la taille

Avant traitement, chaque fichier entrant est vérifié :

```python
if taille_fichier > MAX_INPUT_SIZE_MB × 1024 × 1024:
    # Rejeté → data/error/
    # Métrique : input_rejected_size++
```

### Vérification de la signature

Les signatures valides :
- **ZIP** (CBZ) : `50 4B 03 04`
- **RAR4** (CBR) : `52 61 72 21 1A 07 00`
- **RAR5** (CBR) : `52 61 72 21 1A 07 01 00`

Tout autre format → rejeté avec métrique `input_rejected_signature`.

## Nettoyage manuel

### PowerShell (Windows)

```powershell
# Supprimer les workdirs de plus de N jours
$days = 7
Get-ChildItem ".\data\work\" -Directory |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$days) } |
  Remove-Item -Recurse -Force -Verbose

# Vérifier l'espace disque
$usage = Get-PSDrive N | Select-Object Used, Free
$freeGB = $usage.Free / 1GB
Write-Host "Espace libre : $([math]::Round($freeGB, 2)) Go"
```

### Bash (Linux / macOS)

```bash
# Supprimer les workdirs de plus de 7 jours
find ./data/work/ -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +

# Vérifier l'espace disque
df -h ./data/work/
```

## Tests locaux

### Lancer les tests de robustesse

```powershell
cd services\orchestrator
.\.venv\Scripts\python.exe -m pytest tests/test_robustness.py -v
```

### Démonstration interactive

```powershell
cd services\orchestrator
python demo_robustness.py
```

La démo crée des fichiers temporaires et teste toutes les fonctions de robustesse FS.

## Troubleshooting

### Symptôme : Workdirs non supprimés

**Causes possibles** :
1. `KEEP_WORK_DIR_DAYS` > 0 et les dossiers sont récents
2. Le janitor ne s'exécute que toutes les 600s
3. Les jobs sont encore en cours (`running_job_keys`)

**Solution** :
```bash
# Forcer KEEP_WORK_DIR_DAYS=0 pour suppression immédiate
docker compose restart orchestrator
```

### Symptôme : Erreurs `disk_error` fréquentes

**Causes possibles** :
1. Disque presque plein
2. `DISK_FREE_FACTOR` trop élevé
3. Fichiers entrants très volumineux

**Solution** :
```bash
# Réduire le facteur de sécurité
DISK_FREE_FACTOR=1.5

# Ou augmenter l'espace disque disponible
# Ou activer le nettoyage immédiat
KEEP_WORK_DIR_DAYS=0
```

### Symptôme : Erreurs `pdf_invalid` fréquentes

**Causes possibles** :
1. Problème avec `ocrmypdf` ou Tesseract
2. Fichiers sources corrompus
3. Interruption pendant l'OCR

**Solution** :
1. Vérifier les logs OCR : `docker compose logs ocr-service`
2. Augmenter le timeout : `JOB_TIMEOUT_SECONDS=1200`
3. Vérifier les versions des outils : `GET http://ocr-service:8080/info`

## Références

- [Documentation opérationnelle complète](../../docs/dev/operations.md)
- [Rapport d'implémentation](../../docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_ROBUST-FS_2026-03-03.md)
- [Tests de robustesse](../tests/test_robustness.py)
- [Code source utils.py](../app/utils.py)

---

**Dernière mise à jour** : 2026-03-03

