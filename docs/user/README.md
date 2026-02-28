# Documentation utilisateur — comic2pdf-app

Bienvenue dans la documentation utilisateur de **comic2pdf-app**.

---

## Vue d'ensemble

`comic2pdf-app` convertit automatiquement des archives de bandes dessinées (`.cbz` / `.cbr`) en **PDF avec texte sélectionnable** grâce à l'OCR (reconnaissance optique de caractères via Tesseract).

Le système fonctionne entièrement en local, sans réseau externe, et peut être utilisé de deux façons :

1. **Watch-folder Docker** : glisser des fichiers dans un dossier, les PDFs apparaissent automatiquement dans un dossier de sortie.
2. **Application Desktop JavaFX** : interface graphique pour déposer des fichiers, suivre le traitement et gérer les doublons.

---

## Les deux modes d'utilisation

### Mode watch-folder Docker (recommandé)

La stack Docker surveille en continu le dossier `data/in/`. Dès qu'un fichier `.cbz` ou `.cbr` y apparaît, il est extrait, l'OCR est appliqué, et le PDF final est déposé dans `data/out/`.

**Avantages** : automatique, pas d'interface requise, traitement par lot.

### Mode Desktop JavaFX

L'application desktop offre une interface graphique avec 3 onglets :

| Onglet | Rôle |
|---|---|
| **Doublons** | Affiche les fichiers en attente de décision (doublon détecté), permet de choisir l'action |
| **Jobs** | Suivi temps-réel de tous les jobs (état, étape, tentatives, date) avec rafraîchissement toutes les 3 secondes |
| **Configuration** | Configure l'URL de l'orchestrateur, les concurrences, le timeout et la langue OCR |

**Avantages** : visibilité sur les jobs, gestion des doublons, configuration à chaud.

---

## Concepts importants

### jobKey

Chaque fichier soumis est identifié par un **jobKey** unique formé de deux empreintes SHA-256 :

```
jobKey = fileHash__profileHash
```

- `fileHash` : SHA-256 du contenu du fichier source
- `profileHash` : SHA-256 du **profil canonique** (versions des outils + langue OCR normalisée)

> **Note** : `fra+eng` et `eng+fra` produisent le même `profileHash` (les tokens de langue sont triés avant hachage).

### profileHash et normalisation des langues

Le profil inclut les versions de `7z`, `img2pdf`, `ocrmypdf` et `tesseract`, ainsi que la langue OCR normalisée. Cela garantit qu'un même fichier traité avec des outils différents (mise à jour de Tesseract, par exemple) reçoit un nouveau jobKey et est retraité.

### Doublons

Si un fichier soumis a déjà un jobKey présent dans l'index (même fichier + même profil), il est placé dans `data/hold/duplicates/<jobKey>/` au lieu d'être traité. L'application Desktop affiche ce doublon et propose 3 décisions :

| Décision | Effet |
|---|---|
| `USE_EXISTING_RESULT` | Copie le PDF existant dans `data/out/`, supprime le fichier entrant |
| `DISCARD` | Supprime le fichier entrant sans rien faire |
| `FORCE_REPROCESS` | Retraite le fichier avec un nonce pour forcer un nouveau jobKey |

### Retries (tentatives)

En cas d'échec lors de l'extraction (PREP) ou de l'OCR, le système réessaie automatiquement jusqu'à 3 fois. Au-delà, le fichier est déplacé dans `data/error/` avec son état final.

### États du pipeline

Un job passe par les états suivants :

```
DISCOVERED → PREP_SUBMITTED → PREP_RUNNING → PREP_DONE
           → OCR_SUBMITTED  → OCR_RUNNING  → DONE
```

En cas d'erreur ou de timeout :

```
PREP_RETRY / OCR_RETRY          (tentative en cours)
PREP_TIMEOUT / OCR_TIMEOUT      (dépassement du délai)
ERROR_PREP / ERROR_OCR / ERROR  (tentatives épuisées)
```

---

## Liens vers la documentation détaillée

| Document | Description |
|---|---|
| [installation.md](installation.md) | Prérequis système, installation Docker, build Desktop |
| [usage.md](usage.md) | Dépôt de fichiers, suivi des jobs, gestion des doublons, options OCR |
| [troubleshooting.md](troubleshooting.md) | Résolution des problèmes courants |

---

## Retour à la documentation principale

[← Retour à docs/README.md](../README.md)

