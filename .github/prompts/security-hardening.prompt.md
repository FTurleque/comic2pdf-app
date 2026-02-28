# Feature: Sécurité et durcissement

## Goal
Durcir l’application contre les entrées malveillantes et préparer un mode multi‑utilisateur en ajoutant des contrôles stricts sur les fichiers d’entrée et leur taille. Les services doivent refuser les fichiers dépassant une taille limite ou dont la signature n’est pas valide et isoler les données des utilisateurs.

## Contexte
Les services ne vérifient actuellement que l’extension `.cbz` ou `.cbr` et ne limitent pas la taille des fichiers. Il n’y a pas de séparation entre les utilisateurs ; tous les fichiers sont placés dans `/data`【116166737120233†L24-L47】.

## Tâches
1. Ajoutez une variable d’environnement `MAX_INPUT_SIZE_MB` (par défaut `500`) pour fixer la taille maximale autorisée. Dans l’orchestrateur, après avoir détecté un fichier dans `/in`, vérifiez sa taille (`os.path.getsize`) ; si elle dépasse la limite, déplacez-le dans `/error` avec un message explicite (`input_too_large`) et enregistrez une métrique `input_rejected_size`.
2. Implémentez une fonction `verify_signature(path: Path) -> bool` dans `prep-service` ou un utilitaire partagé qui :
   - Ouvre les premiers octets du fichier et vérifie la signature ZIP (`50 4B 03 04`) ou RAR (`52 61 72 21`) selon la spécification.
   - Si la signature ne correspond pas, refusez le fichier et placez-le en erreur (`invalid_signature`).
3. Modifiez l’orchestrateur pour appeler `verify_signature()` immédiatement après la détection du fichier. Si elle renvoie `False`, déplacez l’entrée dans `/error` et écrivez un rapport dans `logs`.
4. Préparez l’isolation multi‑utilisateur :
   - Introduisez un champ facultatif `user_id` dans `jobKey` et dans `state.json`.
   - Modifiez la hiérarchie des répertoires (`/data`) pour créer un sous-dossier par utilisateur : `/data/users/{userId}/in`, `/work/{userId}`, `/out/{userId}`, `/archive/{userId}`.
   - Mettez à jour l’orchestrateur pour détecter les fichiers par utilisateur et limiter la consommation simultanée selon une configuration (`MAX_JOBS_PER_USER`).
   - Les tests multi‑utilisateurs peuvent être écrits ultérieurement.
5. Ajoutez des tests pour :
   - Vérifier qu’un fichier `.cbz` de 600 Mo est rejeté lorsque `MAX_INPUT_SIZE_MB=500`.
   - Vérifier que `verify_signature()` renvoie `True` pour un vrai ZIP et `False` pour un fichier texte.
   - Vérifier qu’un job est traité dans le bon sous-dossier utilisateur.

## Contraintes
- Ne modifiez pas le mécanisme de déduplication (hash fichier + profil)【116166737120233†L24-L47】, mais ajoutez `user_id` pour isoler les dossiers.
- Les services ne doivent toujours pas accéder à Internet【687954185789220†L24-L30】.
