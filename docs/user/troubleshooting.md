# Résolution de problèmes — comic2pdf-app

Ce guide liste les problèmes courants et leurs solutions.

---

## Mon fichier n'est pas traité

### Symptôme

Le fichier est présent dans `data/in/` mais rien ne se passe.

### Causes possibles et solutions

**1. Fichier encore en `.part`**

L'orchestrateur ignore intentionnellement les fichiers `.part`. Si le fichier est nommé `MonComic.cbz.part`, il ne sera jamais traité.

```powershell
# Windows PowerShell — vérifier les fichiers .part oubliés
Get-ChildItem ".\data\in\" -Filter "*.part"
# Si présents, les renommer :
Rename-Item ".\data\in\MonComic.cbz.part" "MonComic.cbz"
```

```bash
# Linux / macOS
ls ./data/in/*.part
mv ./data/in/MonComic.cbz.part ./data/in/MonComic.cbz
```

**2. Mauvais dossier**

Vérifier que le fichier est bien dans `data/in/` et non dans un sous-dossier ou dans `data/work/`.

**3. Extension incorrecte**

Seuls les fichiers `.cbz` et `.cbr` sont traités. Les extensions `.zip`, `.rar`, `.7z` ne sont pas reconnues.

**4. Stack Docker non démarrée**

```powershell
docker compose ps
# Tous les services doivent être "running"
docker compose up -d
```

---

## Fichier rejeté immédiatement

### Symptôme

Le fichier disparaît de `data/in/` et apparaît dans `data/error/` sans PDF produit. Les métriques `input_rejected_size` ou `input_rejected_signature` augmentent.

### Cause 1 — Taille > 500 Mo

L'orchestrateur rejette les fichiers dont la taille dépasse `MAX_INPUT_SIZE_MB` (défaut : `500` Mo).

**Solution** : vérifier la taille du fichier. Si le fichier est légitimement volumineux, augmenter la limite :

```powershell
# Dans docker-compose.yml, ajouter sous environment de l'orchestrateur :
# MAX_INPUT_SIZE_MB: "1000"
docker compose up -d
```

### Cause 2 — Signature ZIP/RAR invalide

Les fichiers `.cbz` doivent être des archives ZIP valides (magic bytes `PK\x03\x04`).
Les fichiers `.cbr` doivent être des archives RAR valides (magic bytes `Rar!`).

Un fichier corrompu ou renommé frauduleusement sera rejeté.

**Solution** : vérifier l'intégrité du fichier source. Si le fichier est un ZIP renommé en `.cbr`, le renommer en `.cbz`.

```powershell
# Windows PowerShell — vérifier les premiers octets
$bytes = [System.IO.File]::ReadAllBytes("MonComic.cbz")[0..3]
$bytes | ForEach-Object { "{0:X2}" -f $_ }
# Attendu pour CBZ (ZIP) : 50 4B 03 04
```

---

## Erreur `disk_error`

### Symptôme

Un job passe en état `ERROR` et la métrique `disk_error` augmente dans `/metrics`.

### Cause

L'espace disque libre est insuffisant pour traiter le fichier. L'orchestrateur vérifie avant chaque étape PREP que l'espace libre disponible est au moins égal à `taille_fichier × DISK_FREE_FACTOR` (défaut : `2.0`).

### Solution

1. Libérer de l'espace disque (vider `data/work/`, `data/archive/`)
2. Ou réduire le facteur (déconseillé en production) :

```yaml
# docker-compose.yml
environment:
  DISK_FREE_FACTOR: "1.5"
```

Pour nettoyer les workdirs anciens :

```powershell
# Windows PowerShell — supprimer les workdirs de plus de 7 jours
Get-ChildItem ".\data\work\" -Directory |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
  Remove-Item -Recurse -Force
```

---

## PDF final invalide (`pdf_invalid`)

### Symptôme

Un job passe par `OCR_RETRY` plusieurs fois, la métrique `pdf_invalid` augmente, et le job finit en `ERROR_OCR`.

### Cause

Le PDF produit par `ocr-service` ne passe pas la validation : soit le header `%PDF-` est absent, soit la taille est inférieure à `MIN_PDF_SIZE_BYTES` (défaut : `1024` octets).

### Solutions

1. **Vérifier les logs de l'ocr-service** pour identifier l'erreur `ocrmypdf` :

   ```powershell
   docker compose logs ocr-service --tail=50
   ```

2. **Augmenter le niveau de log** (si `LOG_JSON=false`) :

   ```powershell
   docker compose logs --follow orchestrator
   ```

3. Si le problème persiste, le fichier source est peut-être corrompu — tenter de l'ouvrir dans un lecteur de BD pour vérifier.

---

## OCR très lent

### Symptôme

Le traitement d'un fichier prend plusieurs minutes ou dizaines de minutes.

### Causes et solutions

**1. Ressources Docker insuffisantes**

Tesseract est gourmand en CPU et mémoire (minimum 2 Go de RAM recommandé par job OCR). Vérifier les ressources allouées à Docker Desktop.

**2. `OCR_CONCURRENCY` trop élevé**

Si plusieurs jobs OCR tournent en parallèle sur une machine peu puissante, ils se ralentissent mutuellement. Réduire à `1` :

```powershell
# Via l'onglet Configuration du Desktop ou :
curl -X POST http://localhost:18083/config `
  -H "Content-Type: application/json" `
  -d '{"ocr_concurrency": 1}'
```

**3. Fichier très volumineux (nombreuses pages)**

L'OCR est une opération O(n pages). Un volume de 300+ pages peut prendre 5–10 minutes. C'est normal.

---

## Job bloqué / timeout

### Symptôme

Un job reste en état `PREP_RUNNING` ou `OCR_RUNNING` pendant très longtemps, puis passe en `PREP_TIMEOUT` ou `OCR_TIMEOUT`.

### Cause

Le worker (prep-service ou ocr-service) ne répond plus (crash, surcharge). L'orchestrateur détecte l'absence de heartbeat et bascule le job en `*_RETRY`.

### Solutions

1. **Augmenter le timeout** si les fichiers sont légitimement très volumineux :

   ```yaml
   # docker-compose.yml
   environment:
     JOB_TIMEOUT_SECONDS: "1200"  # 20 minutes
   ```

   Ou via l'onglet Configuration (timeout, pas de 60s, plage 60–7200).

2. **Redémarrer le service bloqué** :

   ```powershell
   docker compose restart ocr-service
   ```

3. Les jobs en `PREP_RETRY`/`OCR_RETRY` seront automatiquement relancés lors du prochain tick.

---

## Lire les logs

### Logs standards

```powershell
# Windows PowerShell
docker compose logs --follow orchestrator
docker compose logs --tail=100 prep-service
docker compose logs --tail=100 ocr-service
```

### Logs JSON structurés

Activer le format JSON (une ligne JSON par log) pour faciliter l'analyse avec des outils tiers :

```yaml
# docker-compose.yml — ajouter pour chaque service
environment:
  LOG_JSON: "true"
```

Format d'une ligne de log JSON :

```json
{
  "timestamp": "2026-02-28T10:05:42Z",
  "level": "INFO",
  "service": "orchestrator",
  "message": "Job DONE",
  "jobKey": "abc123__789xyz",
  "stage": "OCR",
  "attempt": 1
}
```

Les champs `jobKey`, `stage`, `attempt` sont optionnels et présents uniquement si pertinents.

### Filtrer les logs JSON avec PowerShell

```powershell
# Afficher uniquement les erreurs
docker compose logs orchestrator | ForEach-Object {
  try { $j = $_ | ConvertFrom-Json; if ($j.level -eq "ERROR") { $_ } } catch {}
}
```

```bash
# Linux / macOS avec jq
docker compose logs orchestrator 2>&1 | grep '^{' | jq 'select(.level == "ERROR")'
```

---

## Récupérer un job en état ERROR

### Symptôme

Un fichier est dans `data/error/` après 3 tentatives échouées.

### Procédure de réinjection manuelle

```powershell
# Windows PowerShell — réinjecter un fichier depuis data/error/
$fichier = "MonComic.cbz"
Copy-Item ".\data\error\$fichier" ".\data\in\$fichier.part"
Rename-Item ".\data\in\$fichier.part" $fichier
```

```bash
# Linux / macOS
fichier="MonComic.cbz"
cp "./data/error/$fichier" "./data/in/${fichier}.part"
mv "./data/in/${fichier}.part" "./data/in/$fichier"
```

> **Note** : si le job échoue à nouveau immédiatement, vérifier les logs pour identifier la cause racine (fichier corrompu, espace disque, ressources insuffisantes).

### Forcer un retraitement complet (nouveau jobKey)

Si le fichier a un jobKey existant dans l'index et que vous souhaitez forcer un nouveau traitement malgré tout, utiliser l'option `FORCE_REPROCESS` depuis l'onglet Doublons du Desktop.

---

## Retour

[← Retour à la documentation utilisateur](README.md)

