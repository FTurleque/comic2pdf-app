# Feature: Observabilité et API HTTP pour l’orchestrateur

## Goal
Améliorer la visibilité du système en exposant un serveur HTTP minimal permettant de consulter l’état des jobs et les métriques, et en structurant les logs en JSON. Cela simplifie le debug et l’intégration avec des outils de supervision.

## Contexte
Actuellement l’orchestrateur n’écrit qu’un fichier `metrics.json` et ne propose aucune interface HTTP. Les logs sont des textes simples. Les variables de concurrence (`PREP_CONCURRENCY`, `OCR_CONCURRENCY`, `MAX_JOBS_IN_FLIGHT`) et les retry sont gérées dans `process_tick()`【116166737120233†L357-L368】.

## Tâches
1. Ajoutez un petit serveur HTTP dans `services/orchestrator/app/main.py` ou dans un nouveau module. Utilisez `http.server` de la bibliothèque standard ou `FastAPI` minimal sans dépendances supplémentaires pour Python 3.12. Le port doit être configurable via `ORCHESTRATOR_PORT` (default `8080`) et l’interface doit écouter sur `0.0.0.0`.
2. Définissez les routes suivantes :
   - `GET /metrics` – renvoie le contenu actuel des métriques dans un objet JSON (compteurs de jobs DONE, ERROR, RUNNING, disk_error, etc.).
   - `GET /jobs` – renvoie la liste des jobs connus, avec leur `jobKey`, `state`, `attempt`, et éventuellement le timestamp `updatedAt`.
   - `GET /jobs/{jobKey}` – renvoie le détail du job correspondant (contenu de `state.json`).
3. Mettez à jour l’orchestrateur pour maintenir une structure en mémoire (ou lire depuis le disque) qui permet de répondre à ces routes de manière efficace. Cette structure doit être thread‑safe si vous utilisez plusieurs threads.
4. Refondez le mécanisme de logs pour utiliser un logger JSON :
   - Créez un formatteur qui sérialise chaque message en JSON avec les champs `timestamp`, `level`, `message`, `jobKey` (si applicable), `stage` (`PREP` ou `OCR`), `attempt` et tout champ utile pour le débogage.
   - Faites en sorte que tous les services (prep, ocr, orchestrateur) utilisent ce format ; ajoutez une option `LOG_JSON=true` pour activer ce format.
5. Ajoutez des tests pour :
   - Vérifier que `GET /metrics` renvoie bien la clé `jobs_done`.
   - Vérifier que `GET /jobs/{jobKey}` renvoie un 404 sur un job inconnu.
   - Vérifier que les logs JSON contiennent les champs attendus.
6. Mettez à jour la documentation pour expliquer comment activer et interroger l’API HTTP et comment analyser les logs JSON.

## Contraintes
- L'API HTTP doit rester interne (pas d'exposition publique) et ne doit pas ajouter d'accès réseau externe【687954185789220†L24-L30】.
- Ne pas bloquer la boucle principale de l’orchestrateur ; utilisez des threads ou `asyncio` pour le serveur afin qu’il coexiste avec `process_loop()`【116166737120233†L357-L368】.
