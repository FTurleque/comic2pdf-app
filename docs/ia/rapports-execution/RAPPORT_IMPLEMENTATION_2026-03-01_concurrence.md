# RAPPORT_IMPLEMENTATION_2026-03-01b

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `Équipe comic2pdf-app`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Tests de concurrence orchestrateur — `test_concurrency.py` |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-03-01` |
| **Auteur(s)** | Équipe comic2pdf-app |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | — |

---

## 2. Contexte et résumé

L'orchestrateur pilote un pipeline `CBZ → PREP → OCR → PDF` avec des limites de parallélisme
(`PREP_CONCURRENCY=2`, `OCR_CONCURRENCY=1`, `MAX_JOBS_IN_FLIGHT=3`). Il n'existait aucun test
automatisé vérifiant que ces limites sont effectivement respectées lors de l'exécution de
plusieurs jobs simultanés. Ce rapport documente la création du fichier `test_concurrency.py`
qui valide de façon déterministe le respect de ces invariants sur 10 jobs complets, sans
dépendance à des outils externes (aucun réseau, aucun Docker).

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Type | Description de la modification |
|---|---|---|
| `services/orchestrator/tests/test_concurrency.py` | **Nouveau** | Tests de concurrence : 2 cas de test pilotant `process_tick()` en boucle sur 10 jobs (rapides) et 6 jobs (lents), avec vérification stricte des limites PREP/OCR/in_flight à chaque tick. |

### Variables d'environnement ajoutées

Aucune.

### Endpoints HTTP ajoutés / modifiés

Aucun.

---

## 4. Étapes pour reproduire / commandes exécutées

```powershell
# Lancer uniquement les tests de concurrence
cd services\orchestrator
.\.venv\Scripts\python.exe -m pytest tests/test_concurrency.py -v

# Lancer toute la suite de l'orchestrateur
.\.venv\Scripts\python.exe -m pytest -q
```

### Résultats des tests

| Module | Tests | Résultat |
|---|---|---|
| `orchestrator` (suite complète) | 83 | ✅ PASS |
| `orchestrator/test_concurrency.py` | 2 | ✅ PASS |

**Détail des 2 nouveaux tests :**

| Test | Description | Résultat |
|---|---|---|
| `test_10_jobs_pipeline_complet` | 10 CBZ → tous DONE + 10 PDF dans /out, limites vérifiées à chaque tick, 60 ticks max | ✅ PASS |
| `test_limites_concurrence_avec_jobs_lents` | 6 CBZ avec maturation 5 ticks — limites tiennent sur toute la durée | ✅ PASS |

---

## 5. Architecture technique du test

### `FakeServiceRouter`

Simulateur stateful qui remplace `submit_prep`, `submit_ocr` et `poll_job` via `monkeypatch` :

- `advance_tick()` : incrémente le compteur interne avant chaque `process_tick()`.
- `submit_prep/ocr(job_key, ...)` : enregistre le tick de soumission.
- `poll_job(url, job_key)` : retourne `RUNNING` jusqu'à `MATURATION` ticks, puis `DONE`.
  - Au premier DONE PREP : crée `work/<jk>/raw.pdf` (`%PDF-1.4\n` + 2 Ko).
  - Au premier DONE OCR : crée `work/<jk>/final.pdf` (`%PDF-1.4\n` + 2 Ko).
- `record_snapshot(in_flight)` : enregistre les compteurs PREP/OCR/total après chaque tick.

### Invariants vérifiés

À **chaque tick** :

```
PREP_RUNNING   ≤ config["prep_concurrency"]    (2)
OCR_RUNNING    ≤ config["ocr_concurrency"]     (1)
len(in_flight) ≤ config["max_jobs_in_flight"]  (3)
```

En **fin de boucle** :

```
jobs DONE == NB_JOBS (10)
in_flight == vide
PDF dans /out == 10
max(snap_prep_running)   ≤ 2
max(snap_ocr_running)    ≤ 1
max(snap_total_inflight) ≤ 3
```

---

## 6. Points d'attention / Limitations

- Le test ne vérifie pas les retries — couvert par `test_orchestrator.py`.
- Les heartbeats absents ne déclenchent pas de stale (délai=1200s) → pas d'interférence.
- La découverte traite un fichier par tick → 60 ticks max suffisants pour 10 jobs.

---

## 7. Liens et références

- Fichier créé : `services/orchestrator/tests/test_concurrency.py`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`

---

## 8. Contact

Pour des questions, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

