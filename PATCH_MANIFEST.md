# PATCH_MANIFEST for branch fix/complete-critical-actions

Date: 2026-03-05
Author (committer): <Nom humain responsable>

This manifest lists the files added or modified as part of the patch that implements the CLI/watch-local mode and the documentation updates required to complete PR traceability.

Files modified/added:

- docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_SPRINT3-CLI-WATCH_2026-03-04.md — mise à jour : ajout d'un auteur humain responsable et placeholder pour l'URL de la PR, ajout de la ligne de traçabilité "Généré par IA — outil: Copilot".
- PATCH_MANIFEST.md — ce fichier (manifeste) listant les fichiers du patch et descriptions.
- docs/ia/rapports-execution/PR_BODY_FIX_COMPLETE_CRITICAL_ACTIONS.md — nouveau : template prêt à coller pour la description de la PR (body) incluant checklist et demande de reviewer.
- services/ocr-service/tests/test_utils.py — modifié : ajout des tests `TestListImagesRecursive` couvrant `list_images_recursive`.
- services/orchestrator/tests/test_utils.py — ajouté : tests utilitaires pour `sha256_file`, `natural_key`, `list_images_recursive` et `now_iso`.

Notes:
- Après création de la PR, remplacer <PR_URL> et <Nom humain responsable> dans `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_SPRINT3-CLI-WATCH_2026-03-04.md` par la valeur réelle.
- Assigner au moins un reviewer humain sur la PR (conformité avec `.github/instructions/reports-docs.instructions.md`).
