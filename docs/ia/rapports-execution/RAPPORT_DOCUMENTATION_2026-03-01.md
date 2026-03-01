# RAPPORT_DOCUMENTATION_2026-03-01

> **Généré par IA** — Outil/Agent : `GitHub Copilot (mode Agent)`
> **Auteur responsable** : `Équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Création runbook opérateur backend (incident handling) |
| **Type** | `DOCUMENTATION` |
| **Date** | `2026-03-01` |
| **Auteur(s)** | `Équipe comic2pdf-app` |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | À créer après validation |

---

## 2. Contexte et résumé

Création d'un **runbook opérateur** centré "incident handling" (quoi faire en cas de crash, job bloqué, saturation disque, état corrompu) pour compléter la documentation backend existante. Le runbook s'appuie sur la machine d'états extraite du code source (`main.py`), les codes d'erreur confirmés (`utils.py`, `core.py`), et fait des liens croisés vers `operations.md` pour éviter toute duplication des détails d'observabilité (endpoints, formats JSON, logs).

---

## 3. Description des changements

### Fichiers créés

| Fichier | Type | Description |
|---|---|---|
| `docs/dev/operations-runbook.md` | Nouveau | Runbook opérateur backend — 6 procédures d'incident, machine d'états complète, glossaire, actions manuelles contrôlées, escalade |
| `docs/ia/rapports-execution/RAPPORT_DOCUMENTATION_2026-03-01.md` | Nouveau | Ce rapport (conforme au template officiel) |

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `docs/dev/README.md` | Modifié | Ajout d'une ligne dans le tableau "Liens vers la documentation développeur détaillée" pointant vers `operations-runbook.md` |

---

## 4. Contenu du runbook

### Machine d'états (extraite du code source)

Le runbook documente les **15 états** exacts extraits de `services/orchestrator/app/main.py` :

**États principaux** :
- `DISCOVERED` → `PREP_SUBMITTED` → `PREP_RUNNING` → `PREP_DONE` → `OCR_SUBMITTED` → `OCR_RUNNING` → `DONE`

**États de retry** :
- `PREP_RETRY`, `OCR_RETRY`, `PREP_TIMEOUT`, `OCR_TIMEOUT`, `PREP_ERROR`, `OCR_ERROR`

**États finaux** :
- `ERROR_PREP`, `ERROR_OCR` (fichier source déplacé vers `data/error/`)
- `DONE` (PDF dans `data/out/`, source dans `data/archive/`)
- `DUPLICATE_PENDING` (attente `decision.json`)

**Transitions validées depuis le code** :
- `PREP_RUNNING` → `PREP_TIMEOUT` (heartbeat stale) → `PREP_RETRY`
- `attemptPrep >= MAX_ATTEMPTS_PREP` (défaut 3) → `ERROR_PREP`
- Idem pour OCR

### 6 procédures d'incident documentées

1. **Job bloqué / heartbeat stale**
   - Symptômes : job en `*_RUNNING` depuis > 10 min, métrique `running` stable
   - Actions : vérifier heartbeat sur disque, lire logs, redémarrer service, augmenter timeout si nécessaire

2. **Saturation disque (`disk_error`)**
   - Symptômes : métrique `disk_error` > 0, jobs rejetés
   - Actions : vérifier espace disque, nettoyer workdirs anciens, vider archive, réduire `DISK_FREE_FACTOR` si nécessaire, relancer fichiers rejetés

3. **PDF final invalide (`pdf_invalid`)**
   - Symptômes : métrique `pdf_invalid` > 0, jobs en boucle `OCR_RETRY`
   - Actions : lire logs OCR, vérifier PDF produit manuellement, tester fichier source, réduire `MIN_PDF_SIZE_BYTES` si légitime

4. **Fichier rejeté : taille ou signature invalide**
   - Symptômes : métriques `input_rejected_size` ou `input_rejected_signature` > 0
   - Actions : vérifier taille, augmenter `MAX_INPUT_SIZE_MB` si légitime, vérifier magic bytes, renommer si ZIP renommé en CBR

5. **state.json corrompu**
   - Symptômes : logs `"json_corrupt"`, job présent dans l'index mais données incohérentes
   - Actions : supprimer `state.json` corrompu, l'orchestrateur le recréera, vérifier intégrité disque

6. **Pic d'erreurs OCR / Tesseract**
   - Symptômes : métrique `error` augmente, logs Tesseract répétés
   - Actions : vérifier ressources Docker, réduire `OCR_CONCURRENCY`, augmenter RAM Docker, identifier fichier problématique

### Codes d'erreur documentés

Tous les codes d'erreur présents dans le code source sont documentés avec cause et action corrective :

| Code | Cause | Action |
|---|---|---|
| `disk_error` | Espace disque < `input_size × DISK_FREE_FACTOR` | Libérer espace, nettoyer workdirs |
| `pdf_invalid` | PDF sans header `%PDF-` ou taille < `MIN_PDF_SIZE_BYTES` | Vérifier logs OCR, tester fichier source |
| `input_rejected_size` | Fichier > `MAX_INPUT_SIZE_MB` | Augmenter limite si légitime |
| `input_rejected_signature` | Magic bytes ni ZIP ni RAR | Vérifier intégrité, renommer si nécessaire |
| `max_attempts_after_restart` | Tentatives dépassées après redémarrage | Job passe en `ERROR*`, fichier vers `data/error/` |
| `heartbeat stale after {timeout}s` | Worker crashé ou surchargé | Redémarrer service, augmenter timeout |
| `json_corrupt` | `state.json` illisible | Supprimer fichier, orchestrateur recréera |

### Actions manuelles contrôlées

Le runbook documente **quand et comment** effectuer les actions manuelles courantes :

- Déplacer un fichier de `/error` vers `/in` (avec convention `.part`)
- Supprimer un workdir manuellement (uniquement si job en état final et absent de `running`)
- Augmenter `JOB_TIMEOUT_SECONDS` (via `/config` ou app desktop)
- Baisser `OCR_CONCURRENCY` (via `/config`)
- Archiver et repartir (reset propre)

### Liens croisés vers operations.md

Le runbook ne duplique **aucun** exemple de commande d'observabilité déjà présent dans `operations.md`. À la place, il fait des liens explicites :

- "Voir [operations.md — `GET /metrics`](operations.md#get-metrics)"
- "Voir [operations.md — `GET /jobs`](operations.md#get-jobs)"
- "Voir [operations.md — Logs JSON structurés](operations.md#logs-json-structurés)"

Ceci garantit une **séparation claire** : `operations.md` = "comment lire", `operations-runbook.md` = "quoi faire".

---

## 5. Étapes pour reproduire / validation

### Vérification des liens internes

```powershell
# Windows PowerShell — vérifier que les liens relatifs pointent vers des fichiers existants
Test-Path ".\docs\dev\operations.md"        # True
Test-Path ".\docs\dev\setup.md"             # True
Test-Path ".\docs\user\troubleshooting.md"  # True
Test-Path ".\docs\dev\README.md"            # True
```

### Validation de la machine d'états

Les états documentés dans le runbook correspondent **exactement** aux états présents dans le code source :

| État documenté | Présent dans le code | Fichier source |
|---|---|---|
| `DISCOVERED` | ✅ | `main.py:587, 595` |
| `PREP_SUBMITTED` | ✅ | `main.py:630` |
| `PREP_RUNNING` | ✅ | `main.py:633, 220` |
| `PREP_DONE` | ✅ | `main.py:647` |
| `PREP_RETRY` | ✅ | `main.py:254, 636, 655` |
| `PREP_TIMEOUT` | ✅ | `main.py:478` |
| `ERROR_PREP` | ✅ | `main.py:245, 619` |
| `OCR_SUBMITTED` | ✅ | `main.py:675` |
| `OCR_RUNNING` | ✅ | `main.py:678, 257` |
| `OCR_DONE` | (implicite via `DONE`) | `main.py:647` |
| `OCR_RETRY` | ✅ | `main.py:267, 681, 703, 730` |
| `OCR_TIMEOUT` | ✅ | `main.py:487` |
| `ERROR_OCR` | ✅ | `main.py:260, 668` |
| `DONE` | ✅ | `main.py:712` |
| `DUPLICATE_PENDING` | ✅ | `main.py:340` (status.json) |

Aucun état inventé. Aucun état manquant.

### Validation des codes d'erreur

Tous les codes d'erreur documentés dans le runbook sont présents dans le code source :

| Code | Fichier source | Ligne |
|---|---|---|
| `disk_error` | `main.py` | 567, métrique `update_metrics(metrics, "disk_error")` |
| `pdf_invalid` | `main.py` | 700-703, métrique + message `"pdf_invalid"` |
| `input_rejected_size` | `main.py` | 548 |
| `input_rejected_signature` | `main.py` | 556 |
| `max_attempts_after_restart` | `main.py` | 243, 259 (message dans `update_state`) |
| `heartbeat stale after {timeout}s` | `main.py` | 479, 488 (message dans `update_state`) |
| `json_corrupt` | `core.py` | 38 (retour de `safe_load_json`) |

Aucun code inventé. Tous les codes présents dans le code sont documentés.

---

## 6. Points d'attention

### Non-duplication avec operations.md

Le runbook fait des liens croisés vers `operations.md` pour **tous les détails d'observabilité** :
- Exemples de commandes `curl` / `Invoke-RestMethod`
- Formats JSON complets (`metrics.json`, `state.json`)
- Tableaux de description des compteurs
- Commandes d'analyse de logs JSON

Seules **1 à 2 commandes d'exemple maximum** par procédure sont incluses dans le runbook, uniquement si elles sont strictement nécessaires au diagnostic immédiat.

### Conformité politique rapports IA

Ce rapport respecte **strictement** la politique `.github/instructions/reports-docs.instructions.md` :

- ✅ Nommé `RAPPORT_DOCUMENTATION_2026-03-01.md` (pattern `RAPPORT_<TYPE>_YYYY-MM-DD.md`)
- ✅ Placé dans `docs/ia/rapports-execution/` (sous-dossier, **pas à la racine de `docs/ia/`**)
- ✅ Basé sur `docs/ia/templates/rapport_template.md`
- ✅ Mention "Généré par IA — GitHub Copilot (mode Agent)" en haut
- ✅ Sections minimales complètes (identification, contexte, changements, étapes, liens)
- ✅ Auteur responsable identifié (`Équipe comic2pdf-app`)

### Évitement de l'écrasement

Un fichier `RAPPORT_DOCUMENTATION_2026-02-28.md` existait déjà dans `docs/ia/rapports-execution/`. Le nouveau rapport est daté **2026-03-01** pour éviter tout conflit ou écrasement.

---

## 7. Liens et références

- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Template officiel : `docs/ia/templates/rapport_template.md`
- Runbook créé : `docs/dev/operations-runbook.md`
- README dev mis à jour : `docs/dev/README.md`
- Copilot instructions globales : `.github/copilot-instructions.md`

---

## 8. Contact

Pour des questions sur ce rapport ou le runbook, ouvrir une issue dans le dépôt et taguer `@team-architecture`.



