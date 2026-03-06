# PATCH_MANIFEST for branch chore/security-compliance-2026-03-06

Date: 2026-03-06
Author (committer): <Nom humain responsable — à compléter>

Branch: chore/security-compliance-2026-03-06

This manifest lists the files added or modified as part of the security & compliance patch:
audit CI (pip-audit gating), Dependabot, licences snapshot, Ghostscript decision.

Files added:
- .github/dependabot.yml — nouveau : configuration Dependabot pip (4 cibles : prep-service,
  ocr-service, orchestrator, tools) + github-actions. Schedule weekly, groupes patch-minor.
  Comportement limité sans pinning — documenté. PR chore/pin-dependencies requise ensuite.
- .github/workflows/dependency-audit.yml — nouveau : workflow dédié gating sécurité.
  Job A pip-audit-gating (bloquant HIGH/CRITICAL en PR/push, warn-only en schedule,
  python -m pip_audit, arbre transitif résolu via pip install avant audit).
  Job B licenses-snapshot (non bloquant, artefact CI 30j, UNKNOWN signalés sans fail).
- docs/compliance/python-deps-licenses.md — nouveau (dossier docs/compliance/ créé) :
  snapshot versionné des licences runtime directes Python (4 services). Versions "unpinned"
  jusqu'à chore/pin-dependencies. Binaires système exclus → THIRD_PARTY_NOTICES.md.
- docs/security/dependencies.md — nouveau (dossier docs/security/ créé) :
  politique d'audit complète (outils, fréquence, seuils, note versions non épinglées),
  décision Ghostscript AGPL Option A (conserver), ticket migration feat/ghostscript-alternative,
  Dependabot & pinning (prérequis Allow auto-merge, PR chore/pin-dependencies).
- docs/ia/rapports-execution/RAPPORT_SECURITE_2026-03-06.md — nouveau : rapport IA
  conforme au template rapport_template.md, type SECURITE, Généré par IA — GitHub Copilot.

Files modified:
- .github/workflows/ci.yml — commentaires de coexistence ajoutés sur python-audit (Job 2)
  et java-audit (Job 5) : REPORTING UNIQUEMENT, plan de sortie après 1–2 cycles.
- PATCH_MANIFEST.md — ce fichier, nouvelle entrée.

Next step (obligatoire après merge) :
- Créer PR chore/pin-dependencies : pip-tools (requirements.in → pip-compile →
  requirements.txt épinglé) pour les 4 cibles Python. Sans cette PR, Dependabot pip
  reste décoratif et l'audit CI reste un "meilleur cas" non reproductible.
- Créer issue feat/ghostscript-alternative : évaluer pikepdf + patch ocrmypdf sans gs.

Notes:
- Après création de la PR, remplacer <Nom humain responsable> et <PR_URL> dans
  docs/ia/rapports-execution/RAPPORT_SECURITE_2026-03-06.md.
- Assigner au moins un reviewer humain (conformité reports-docs.instructions.md).

---

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
