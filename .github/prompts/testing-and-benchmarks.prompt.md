# Feature: Tests et benchmarks avancés pour l’orchestrateur

## Goal
Renforcer la robustesse de l’orchestrateur par des tests supplémentaires couvrant les cas difficiles (concurrence, timeouts, doublons) et fournir des benchmarks de performance pour mesurer l’impact des améliorations.

## Contexte
Les tests actuels couvrent des cas unitaires de base. Ils n'exercent pas la concurrence configurée (`PREP_CONCURRENCY`, `OCR_CONCURRENCY`) ni les mécanismes de timeout et de retry【116166737120233†L357-L368】. Aucune mesure de performance n'est produite.

## Tâches
1. Créez des tests d’intégration qui simulent plusieurs jobs en parallèle :
   - Utilisez des mocks pour `prep-service` et `ocr-service` afin de simuler des durées différentes (ex : PREP = 1 s, OCR = 3 s).
   - Vérifiez que l’orchestrateur lance au plus `PREP_CONCURRENCY` jobs PREP et au plus `OCR_CONCURRENCY` jobs OCR simultanément.
   - Vérifiez que les jobs se terminent tous et que l’état final est `DONE`.
2. Créez un test qui vérifie la logique de timeout :
   - Simulez un job PREP qui ne met pas à jour son `heartbeat` pendant plus longtemps que `JOB_TIMEOUT_SECONDS`.
   - Vérifiez que l’orchestrateur annule le job (requeue ou erreur) après le délai.
3. Créez un test pour la gestion des doublons et `FORCE_REPROCESS` :
   - Simulez l’arrivée d’un second fichier avec le même `jobKey`.
   - Vérifiez qu’il est placé en attente dans `hold/duplicates`.
   - Ajoutez un fichier `decision.json` avec `FORCE_REPROCESS` et vérifiez que le job est lancé avec un nouveau runId (car `jobKey` reste identique).
4. Ajoutez un script `benchmarks.py` dans `services/orchestrator` qui :
   - Permet de lancer N conversions de test et de mesurer le temps moyen des étapes PREP et OCR.
   - Mesure l’utilisation CPU (en utilisant `psutil` dev‑only).
   - Supporte différentes valeurs de `PREP_CONCURRENCY` et `OCR_CONCURRENCY` pour mesurer l’évolutivité.
   - Produit un rapport en JSON.
5. Mettez à jour `run_tests.ps1` pour inclure les nouveaux tests et expliquer comment exécuter les benchmarks manuellement.

## Contraintes
- Les tests doivent utiliser des mocks et ne doivent pas exiger l’installation de `7z` ou `ocrmypdf` (sauf marquage `@pytest.mark.integration` et documenté).
- Le benchmark peut nécessiter les outils ; documentez clairement cette dépendance et ne l’exécutez pas par défaut.
