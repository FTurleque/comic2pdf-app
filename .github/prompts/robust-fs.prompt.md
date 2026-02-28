# Feature: Robust filesystem operations

## Goal
Améliorer la robustesse de `comic2pdf-app` en gérant automatiquement la propreté et la sécurité du système de fichiers de travail (`/work`) et en détectant les problèmes d'espace disque. À la fin de chaque job, il faut nettoyer les fichiers temporaires et supprimer les dossiers de travail selon une politique configurable. Avant de déplacer le PDF final vers `/out`, vérifier qu'il est valide et non corrompu. Refuser le traitement s'il n'y a pas assez d'espace disque pour l'extraction et l'assemblage des pages.

## Contexte
Actuellement, après chaque job terminé, le dossier `/work/<jobKey>/` reste en place【116166737120233†L357-L368】. Il n'y a pas de vérification d'intégrité du PDF final, et aucune protection contre un disque plein. Le système réessaie seulement trois fois par étape et garde la trace de l'état des jobs dans `state.json`【116166737120233†L436-L452】.

## Tâches
1. Ajoutez une variable d'environnement `KEEP_WORK_DIR_DAYS` (par défaut `7`). Après la réussite d'un job, l'orchestrateur doit supprimer le dossier `/work/<jobKey>/` immédiatement si `KEEP_WORK_DIR_DAYS=0`, ou planifier sa suppression après X jours. Utilisez un thread ou un cron interne qui parcourt régulièrement `/work` et supprime les dossiers plus anciens que la limite.
2. Ajoutez une fonction `validate_pdf(path: Path) -> bool` dans `prep-service` ou dans un utilitaire partagé. Elle doit:
   - Ouvrir le fichier en binaire et vérifier qu'il commence par `%PDF`.
   - Vérifier que la taille est supérieure à un seuil (ex : 1 Ko).
   - Optionnel: utiliser `PyPDF2` pour tenter de lire les pages (bibliothèque dev‑only).
   - Renvoie `True` si le fichier semble valide, `False` sinon.
3. Avant de déplacer `final.pdf` dans `/out`, appelez `validate_pdf()`. Si la validation échoue, marquez le job en `ERROR`, incrémentez `attempts`, et nettoyez `final.pdf.tmp` sans déplacer.
4. Ajoutez une vérification d'espace disque libre avant de lancer l'étape PREP : utilisez `shutil.disk_usage(WORK_DIR)` pour obtenir l'espace libre, comparez avec la taille du fichier d'entrée multipliée par un facteur (ex : *2*). Si l'espace disponible est insuffisant, passez le job en `ERROR` avec un message clair et incrémentez un compteur `disk_error` dans les métriques.
5. Ajoutez une métrique `disk_error` dans `metrics.json` pour compter les jobs interrompus pour cause de disque saturé.
6. Ajoutez des tests unitaires et d'intégration :
   - Simulez un job terminé et vérifiez que le dossier de travail est supprimé selon la politique configurée.
   - Simulez un fichier PDF tronqué et vérifiez que `validate_pdf()` renvoie `False`.
   - Simulez un espace disque insuffisant (en mockant `shutil.disk_usage`) et vérifiez que l'orchestrateur déclenche une erreur.

## Contraintes et recommandations
- Gardez le code testable en isolant les fonctions pures dans un module (`app/utils.py`) et en utilisant des mocks (`pytest-mock`) pour simuler l'espace disque et les fichiers.
- Respectez les invariants : pas d'accès réseau externe et pas de modification de la politique de retry actuelle (3 tentatives par étape)【687954185789220†L24-L30】.
