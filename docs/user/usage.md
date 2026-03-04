# Utilisation — comic2pdf-app

Ce guide détaille l'utilisation quotidienne de `comic2pdf-app` : dépôt de fichiers, suivi des jobs, gestion des doublons et options OCR.

---

## Mode watch-folder

### Convention `.part` → rename

Pour éviter que l'orchestrateur ne commence à traiter un fichier encore en cours de copie, la convention imposée est :

1. Copier le fichier en le nommant avec l'extension `.part`
2. Renommer le fichier en son nom définitif (`.cbz` ou `.cbr`) **une fois la copie terminée**

L'orchestrateur ignore les fichiers `.part` et ne démarre le traitement qu'après le rename.

### Commandes de dépôt

#### Windows (PowerShell)

```powershell
# Déposer un seul fichier
Copy-Item "C:\mes-bd\MonComic.cbz" ".\data\in\MonComic.cbz.part"
Rename-Item ".\data\in\MonComic.cbz.part" "MonComic.cbz"
```

```powershell
# Déposer un lot de fichiers depuis un dossier
Get-ChildItem "C:\mes-bd\" -Filter "*.cbz" | ForEach-Object {
    $dest = ".\data\in\$($_.Name).part"
    Copy-Item $_.FullName $dest
    Rename-Item $dest $_.Name
}
```

#### Linux / macOS (bash)

```bash
# Déposer un seul fichier
cp "/mes-bd/MonComic.cbz" "./data/in/MonComic.cbz.part"
mv "./data/in/MonComic.cbz.part" "./data/in/MonComic.cbz"
```

```bash
# Déposer un lot de fichiers
for f in /mes-bd/*.cbz; do
  name=$(basename "$f")
  cp "$f" "./data/in/${name}.part"
  mv "./data/in/${name}.part" "./data/in/${name}"
done
```

### Via l'application Desktop

Dans l'onglet **Doublons**, utiliser le bouton de dépôt de fichier : l'application effectue automatiquement la copie `.part` puis le rename atomique (`Files.move ATOMIC_MOVE`).

---

## Description des dossiers `data/`

| Dossier | Rôle | Contenu typique |
|---|---|---|
| `data/in/` | Fichiers entrants à traiter | `.cbz`, `.cbr` (ignorer `.part`) |
| `data/out/` | PDFs finaux produits | `MonComic__job-<jobKey>.pdf` |
| `data/work/` | Dossiers de travail temporaires par job | `<jobKey>/raw.pdf`, `<jobKey>/state.json`, `<jobKey>/*.heartbeat` |
| `data/archive/` | Fichiers sources traités avec succès | `.cbz` / `.cbr` archivés |
| `data/error/` | Fichiers ayant dépassé le nombre maximal de tentatives | `.cbz` / `.cbr` + `state.json` (état ERROR) |
| `data/hold/duplicates/` | Doublons en attente de décision | `<jobKey>/` contenant `decision.json` (écrit par le Desktop) |
| `data/reports/duplicates/` | Rapports JSON sur les doublons | `<jobKey>.json` |
| `data/index/` | Index global de tous les jobs | `jobs.json`, `metrics.json` |

> **Important** : ne jamais modifier manuellement `data/index/jobs.json` ni `data/index/metrics.json` pendant que la stack Docker tourne.

---

## Suivi des jobs

### Via l'onglet Jobs (Desktop)

L'onglet **Jobs** affiche la liste de tous les jobs avec les colonnes :

| Colonne | Description |
|---|---|
| `jobKey` | Identifiant unique du job |
| `Fichier` | Nom du fichier source |
| `État` | État courant du pipeline (ex : `DONE`, `OCR_RUNNING`) |
| `Étape` | Étape courante (`PREP` / `OCR`) |
| `Tentative` | Numéro de tentative courante (1, 2 ou 3) |
| `Mis à jour` | Date/heure ISO de la dernière mise à jour |

Le bouton **Ouvrir dossier out/** ouvre directement `data/out/` dans l'explorateur de fichiers.

### Via l'endpoint HTTP

```powershell
# Windows PowerShell — liste tous les jobs
Invoke-RestMethod http://localhost:18083/jobs

# Détail d'un job spécifique
Invoke-RestMethod "http://localhost:18083/jobs/<jobKey>"
```

```bash
# Linux / macOS
curl http://localhost:18083/jobs
curl "http://localhost:18083/jobs/<jobKey>"
```

### Format d'un `state.json` (exemple type)

```json
{
  "jobKey": "abc123def456__789xyz",
  "inputFile": "MonComic.cbz",
  "state": "DONE",
  "stage": "OCR",
  "attempt": 1,
  "workDir": "/data/work/abc123def456__789xyz",
  "rawPdf": "/data/work/abc123def456__789xyz/raw.pdf",
  "finalPdf": "/data/out/MonComic__job-abc123def456__789xyz.pdf",
  "createdAt": "2026-02-28T10:00:00Z",
  "updatedAt": "2026-02-28T10:05:42Z"
}
```

---

## Gestion des doublons

### Quand un doublon est-il détecté ?

Un doublon est détecté lorsqu'un fichier soumis possède un `jobKey` déjà présent dans l'index (`data/index/jobs.json`). Cela signifie que le même fichier avec le même profil OCR a déjà été traité (ou est en cours de traitement).

### Rapport JSON (exemple type)

```json
{
  "jobKey": "abc123def456__789xyz",
  "incomingFile": "MonComic.cbz",
  "existingState": {
    "jobKey": "abc123def456__789xyz",
    "inputFile": "MonComic.cbz",
    "state": "DONE",
    "finalPdf": "/data/out/MonComic__job-abc123def456__789xyz.pdf",
    "updatedAt": "2026-02-01T14:22:00Z"
  },
  "detectedAt": "2026-02-28T10:00:00Z"
}
```

### Les 3 décisions disponibles

| Décision | Description | Effet |
|---|---|---|
| `USE_EXISTING_RESULT` | Utiliser le PDF déjà produit | Copie le PDF existant dans `data/out/`, supprime le fichier entrant de `data/hold/duplicates/` |
| `DISCARD` | Ignorer le fichier entrant | Supprime le fichier entrant sans rien faire |
| `FORCE_REPROCESS` | Forcer un retraitement complet | Remet le fichier dans `data/in/` avec un nonce pour générer un nouveau `jobKey` et relancer le pipeline |

### Comment décider via l'interface

1. Ouvrir l'onglet **Doublons** dans l'application Desktop
2. La liste affiche les doublons en attente (fichier, état du job existant)
3. Sélectionner une ligne et cliquer sur le bouton correspondant à la décision souhaitée
4. L'application écrit `decision.json` dans `data/hold/duplicates/<jobKey>/`
5. L'orchestrateur lit la décision au prochain tick et exécute l'action

---

## Options OCR

### Langue OCR

La langue OCR est configurable via :

- **Variable d'environnement** `OCR_LANG` (défaut : `fra+eng`)
- **Onglet Configuration** de l'application Desktop (champ "Langue OCR")

Format : codes Tesseract séparés par `+` (ex : `fra`, `eng`, `fra+eng`, `deu`, `spa+eng`).

> **Normalisation** : `fra+eng` et `eng+fra` sont équivalents — les tokens sont triés alphabétiquement avant le calcul du `profileHash`. Changer l'ordre des langues ne relance donc **pas** le traitement.

### Paramètres exposés dans l'onglet Configuration

| Paramètre | Défaut | Plage | Description |
|---|---|---|---|
| `PREP_CONCURRENCY` | `2` | 1–16 | Nombre de jobs PREP simultanés |
| `OCR_CONCURRENCY` | `1` | 1–8 | Nombre de jobs OCR simultanés |
| Timeout (s) | `600` | 60–7200 (pas 60s) | Délai max par étape avant timeout |
| Langue OCR | `fra+eng` | codes Tesseract | Langue(s) pour Tesseract |

Cliquer sur **Appliquer** :
1. Sauvegarde la configuration localement (`config.json`)
2. Envoie un `POST /config` à l'orchestrateur pour appliquer les changements à chaud

---

## Mode CLI (sans Docker)

### Conversion ponctuelle

```powershell
# Windows PowerShell
python tools/cli.py MonComic.cbz --lang fra+eng --out ./pdfs/
```

```bash
# Linux / macOS
python3 tools/cli.py MonComic.cbz --lang fra+eng --out ./pdfs/
```

### Options disponibles

| Option | Défaut | Description |
|---|---|---|
| `--lang` | `fra+eng` | Langue(s) OCR Tesseract (ex : `fra`, `eng`, `fra+eng`) |
| `--out` | `.` | Dossier de sortie du PDF |
| `--no-ocr` | off | Produire uniquement le raw.pdf sans OCR |
| `--keep-temp` | off | Conserver le dossier de travail temporaire |
| `--check-deps` | — | Vérifier les dépendances et quitter |

### Exemples

```powershell
# Vérifier les dépendances
python tools/cli.py --check-deps

# Conversion sans OCR (rapide)
python tools/cli.py MonComic.cbz --no-ocr --out ./pdfs/

# Conversion avec langue allemande
python tools/cli.py MonComic.cbz --lang deu --out ./pdfs/

# Conserver le dossier de travail pour débogage
python tools/cli.py MonComic.cbz --keep-temp --out ./pdfs/
```

### Nommage de la sortie

Le PDF produit suit la même convention que le mode Docker :

```
<nom_sans_extension>__job-<fileHash>__<profileHash>.pdf
```

---

## Mode watch-folder local (sans Docker)

### Démarrage de la surveillance

```powershell
# Windows PowerShell
python tools/watch_local.py --in ./data/in --out ./data/out
```

```bash
# Linux / macOS
python3 tools/watch_local.py --in ./data/in --out ./data/out
```

### Options disponibles

| Option | Défaut | Description |
|---|---|---|
| `--in` | `./data/in` | Dossier d'entrée à surveiller |
| `--out` | `./data/out` | Dossier de sortie des PDFs |
| `--lang` | `fra+eng` | Langue(s) OCR |
| `--no-ocr` | off | Désactiver l'OCR |
| `--keep-temp` | off | Conserver les dossiers temporaires |
| `--poll-interval` | `2` | Intervalle de polling en secondes |
| `--hold-dir` | `./data/hold/duplicates` | Dossier pour les doublons |
| `--check-deps` | — | Vérifier les dépendances et quitter |

### Convention de dépôt

La même convention `.part` → rename est respectée :

```powershell
# Windows PowerShell — dépôt sûr
Copy-Item "MonComic.cbz" ".\data\in\MonComic.cbz.part"
Rename-Item ".\data\in\MonComic.cbz.part" "MonComic.cbz"
```

```bash
# Linux / macOS
cp MonComic.cbz ./data/in/MonComic.cbz.part
mv ./data/in/MonComic.cbz.part ./data/in/MonComic.cbz
```

Le watcher ignore les fichiers `.part` et ne démarre le traitement qu'après le rename.

### Gestion des doublons (mode local)

En mode local, les doublons sont détectés via le même mécanisme `jobKey = fileHash__profileHash`. Un doublon est déplacé dans `--hold-dir/<jobKey>/` et un message est affiché :

```
[watch_local] DOUBLON détecté : 'MonComic.cbz'
  jobKey   : abc123__def456
  Existant : ./data/out/MonComic__job-abc123__def456.pdf
  Fichier déplacé vers : ./data/hold/duplicates/abc123__def456/20260304-120000__MonComic.cbz
```

Pour forcer le retraitement, supprimer manuellement l'entrée de `hold/` et redéposer le fichier.

### État persisté

Le watcher maintient un fichier `processed.json` dans le dossier `--out` pour éviter les retraitements entre redémarrages :

```json
{
  "abc123__def456": {
    "fileName": "MonComic.cbz",
    "jobKey": "abc123__def456",
    "processedAt": "2026-03-04T12:00:00Z",
    "outputPdf": "./data/out/MonComic__job-abc123__def456.pdf"
  }
}
```

---

## Retour


