# Comic2PDF (CBR/CBZ -> PDF searchable)

Objectif : convertir des fichiers `.cbr` / `.cbz` en **PDF avec texte sélectionnable** (OCR) via une chaîne **Docker** fiable.

## 1) Prérequis
- Docker + Docker Compose

## 2) Lancer en mode Docker (watch-folder)
Depuis la racine :
```bash
docker compose up -d --build
```

Arborescence des volumes (créée automatiquement dans `./data`) :
- `data/in` : déposer des `.cbz` / `.cbr`
- `data/out` : récupérer les PDFs
- `data/work` : jobs temporaires
- `data/hold/duplicates` : doublons en attente de décision
- `data/reports/duplicates` : rapports JSON consommés par l'app Desktop
- `data/error` : jobs en erreur (après 3 tentatives par étape)

### Dépôt fiable (anti-fichier-en-cours-de-copie)
Copier en `.part`, puis renommer quand la copie est finie :
```bash
cp "/chemin/MonComic.cbz" "./data/in/MonComic.cbz.part"
mv "./data/in/MonComic.cbz.part" "./data/in/MonComic.cbz"
```

### Concurrence (config)
Modifier les env vars dans `docker-compose.yml` :
- `PREP_CONCURRENCY`
- `OCR_CONCURRENCY`
- `MAX_JOBS_IN_FLIGHT`
- `MAX_ATTEMPTS_PREP=3`
- `MAX_ATTEMPTS_OCR=3`

## 3) App Desktop (JavaFX)
L'app desktop sert de **front** :
- déposer un fichier dans `in` (copie + rename `.part` -> final)
- afficher les doublons (rapport) et écrire une décision

### Build & run
```bash
cd desktop-app
mvn -q -DskipTests package
mvn -q javafx:run
```

> L'app desktop suppose que la stack docker tourne (mode "orchestrateur + services").

## 4) Décisions doublons
La clé de job = `fileHash__profileHash` (SHA-256), où le **profil inclut les versions des outils**.

Si un jobKey existe déjà, l'orchestrateur place le fichier dans :
`data/hold/duplicates/<jobKey>/...` et écrit :
`data/reports/duplicates/<jobKey>.json`

L'app desktop écrit une décision dans :
`data/hold/duplicates/<jobKey>/decision.json`

Décisions supportées :
- `USE_EXISTING_RESULT`
- `DISCARD`
- `FORCE_REPROCESS` (re-traitement forcé avec un nonce)

## 5) Structure
- `services/prep-service` : extraction (7z) + img2pdf -> raw.pdf
- `services/ocr-service`  : ocrmypdf + tesseract -> final.pdf
- `services/orchestrator` : watch-folder, pipeline, gestion doublons, concurrence

