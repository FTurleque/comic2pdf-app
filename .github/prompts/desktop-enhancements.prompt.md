# Feature: Améliorations de l’application Desktop – suivi et configuration

## Goal
Améliorer l’application JavaFX afin d’offrir aux utilisateurs une vue en temps réel des jobs et la possibilité de configurer les paramètres clés sans modifier le fichier docker-compose. Ajouter une fonctionnalité pour ouvrir le dossier de sortie du job.

## Contexte
L’interface actuelle gère uniquement les doublons. Il manque un écran de suivi des jobs (RUNNING/DONE/ERROR) et un moyen de modifier la concurrence, la langue OCR et le timeout via l’interface.

## Tâches
1. Créez une nouvelle vue « Jobs » dans l’application JavaFX :
   - Afficher une table avec `jobKey`, `nom du fichier`, `étape`, `state`, `progression` et `updatedAt`.
   - Afficher la progression OCR si elle est fournie par l’API `/jobs/{jobKey}` (par exemple en pourcentage).
   - Permettre de sélectionner un job et d’ouvrir le dossier de sortie à l’aide d’un bouton qui utilise `Desktop.getDesktop().open(outDir.toFile())`.
   - Rafraîchir la table périodiquement (toutes les X secondes) en interrogeant l’API HTTP de l’orchestrateur (voir prompt Observabilité).
2. Ajoutez un écran ou un dialogue « Configuration » pour modifier :
   - `PREP_CONCURRENCY`
   - `OCR_CONCURRENCY`
   - `JOB_TIMEOUT_SECONDS`
   - `Langue OCR` (liste déroulante)
   Enregistrez ces paramètres dans un fichier de configuration local (ex : `config.json`) et envoyez‑les à l’orchestrateur via un endpoint `POST /config`.
3. Mettez à jour l’orchestrateur pour accepter les modifications de configuration à chaud via `POST /config` et appliquer immédiatement les nouvelles valeurs.
4. Refactorez l’ancienne logique de gestion des doublons pour utiliser `DuplicateService` (comme décrit dans prompt 05) et s’intégrer proprement avec la vue « Jobs ».
5. Ajoutez des tests unitaires avec JUnit 5 pour vérifier :
   - La sérialisation/désérialisation du fichier de configuration.
   - L’appel correct de l’endpoint `/config`.
   - L’ouverture du dossier de sortie dans `DuplicateService`.

## Contraintes
- Ne pas bloquer l’interface pendant les appels réseau.
- Ne pas ajouter de tests UI lourds ; concentrez‑vous sur les classes de service.
