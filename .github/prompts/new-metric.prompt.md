---
description: Ajouter une nouvelle métrique dans l'orchestrateur (compteur JSON pur)
---

# Prompt — new-metric

## Goal
Ajouter un nouveau compteur dans le système de métriques de l'orchestrateur,
persisté dans `data/index/metrics.json` à chaque tick.

## Context

- **Fichiers existants** :
  - `services/orchestrator/app/core.py` → `make_empty_metrics`, `update_metrics`, `write_metrics`
  - `services/orchestrator/app/main.py` → `process_tick` (appelle `update_metrics` + `write_metrics`)
  - `services/orchestrator/tests/test_core.py` → classe `TestMetrics`
- **Métriques actuelles** : `done`, `error`, `running`, `queued`.
- **Principe** : JSON pur, zéro Prometheus, zéro dépendance externe.
- **Persistance** : `data/index/metrics.json` (écrasé à chaque tick via `atomic_write_json`).

## Task
Ajouter la métrique `<nom_metrique>` qui compte `<description de l'événement>`.

## Steps

### 1. Lire le code existant
```
read_file services/orchestrator/app/core.py          # make_empty_metrics, update_metrics
read_file services/orchestrator/app/main.py          # process_tick (chercher "update_metrics")
read_file services/orchestrator/tests/test_core.py   # TestMetrics
```

### 2. Ajouter la clé dans `make_empty_metrics`

Dans `services/orchestrator/app/core.py` :

```python
def make_empty_metrics() -> dict:
    """
    Retourne un dict de métriques initialisé à zéro.
    ...
    """
    return {
        "done": 0,
        "error": 0,
        "running": 0,
        "queued": 0,
        "<nom_metrique>": 0,    # ← ajouter ici avec commentaire bref
        "updatedAt": "",
    }
```

> `update_metrics` incrémente uniquement les clés présentes dans le dict.
> Il n'est **pas** nécessaire de modifier `update_metrics`.

### 3. Identifier où appeler `update_metrics` dans `process_tick`

Localiser l'événement dans `services/orchestrator/app/main.py` :

| Événement | Emplacement dans `process_tick` |
|---|---|
| Job découvert | Section "Découverte", après `in_flight[job_key] = {...}` |
| Doublon détecté | Section "Découverte", après `write_duplicate_report(...)` |
| Job PREP soumis | Section "Planification PREP", après `meta["stage"] = "PREP_RUNNING"` |
| Job PREP en erreur | Section "Planification PREP", après `del in_flight[job_key]` (erreur MAX) |
| Job OCR soumis | Section "Planification OCR" |
| Job terminé (DONE) | Section "Polling OCR", après `del in_flight[job_key]` (succès) |
| Job timeout | `check_stale_jobs` (dans `main.py`) |

Ajouter l'appel :
```python
update_metrics(metrics, "<nom_metrique>")
```

### 4. Écrire les tests dans `TestMetrics`

Dans `services/orchestrator/tests/test_core.py` :

```python
def test_update_incremente_<nom_metrique>(self):
    """update_metrics('<nom_metrique>') incrémente uniquement le bon compteur."""
    m = make_empty_metrics()
    update_metrics(m, "<nom_metrique>")
    assert m["<nom_metrique>"] == 1
    assert m["done"] == 0         # les autres ne bougent pas
    assert m["error"] == 0

def test_write_metrics_contient_<nom_metrique>(self, tmp_path):
    """metrics.json contient la clé '<nom_metrique>' avec la bonne valeur."""
    m = make_empty_metrics()
    update_metrics(m, "<nom_metrique>")
    update_metrics(m, "<nom_metrique>")  # 2 fois
    write_metrics(m, str(tmp_path))

    with open(tmp_path / "metrics.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "<nom_metrique>" in data
    assert data["<nom_metrique>"] == 2
    assert "updatedAt" in data
```

### 5. Valider
```powershell
cd services\orchestrator
.\.venv\Scripts\python -m pytest -q
```

### 6. Documenter (si la métrique est exposée à l'utilisateur)
Mettre à jour `README.md` en ajoutant la métrique dans la liste des indicateurs disponibles.

## Constraints

- **Pas de Prometheus, pas de StatsD, pas d'HTTP** : JSON pur uniquement.
- **`update_metrics` ne doit pas crasher** sur un événement inconnu — il l'ignore silencieusement.
- **`make_empty_metrics()` est la source de vérité** pour les clés valides.
- **Uniquement des compteurs entiers** (pas de pourcentages, pas de moyennes, pas de jauges).
- **Un seul fichier** : `data/index/metrics.json` (pas de nouveau fichier de métriques).
- La clé `"updatedAt"` est toujours mise à jour par `write_metrics` — ne pas la gérer manuellement.

## Examples

### Exemple 1 : compteur `duplicates_detected`

```python
# core.py — make_empty_metrics
"duplicates_detected": 0,   # nombre de doublons détectés depuis le démarrage

# main.py — process_tick, section Découverte
if existing:
    write_duplicate_report(job_key, staging_path, existing, profile)
    update_metrics(metrics, "duplicates_detected")
    continue
```

### Exemple 2 : compteur `prep_retries`

```python
# core.py — make_empty_metrics
"prep_retries": 0,   # nombre de tentatives PREP supplémentaires (après la 1ère)

# main.py — process_tick, section Planification PREP
# (dans le bloc où meta["stage"] est mis à PREP_RETRY après une erreur)
meta["stage"] = "PREP_RETRY"
update_metrics(metrics, "prep_retries")
```

### Exemple 3 : compteur `jobs_timed_out`

```python
# core.py — make_empty_metrics
"jobs_timed_out": 0,   # nombre de jobs basculés en retry à cause d'un heartbeat périmé

# main.py — check_stale_jobs
if is_heartbeat_stale(hb_path, timeout_s):
    update_state(job_key, {...})
    meta["stage"] = "PREP_RETRY"
    # NOTE : check_stale_jobs ne reçoit pas "metrics" en paramètre actuellement.
    # Si nécessaire, passer metrics en paramètre supplémentaire à check_stale_jobs,
    # puis appeler update_metrics(metrics, "jobs_timed_out") ici.
```

> **Note sur `check_stale_jobs`** : si le compteur doit être incrémenté depuis `check_stale_jobs`,
> il faut ajouter `metrics: dict` comme paramètre et l'appeler avec le dict partagé depuis `process_tick`.

