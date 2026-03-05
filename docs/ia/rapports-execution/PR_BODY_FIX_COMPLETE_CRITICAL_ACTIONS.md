# PR Body Template — fix/complete-critical-actions

Titre : fix: complete critical PR actions — rapport IA & manifest

Résumé

Cette PR finalise les actions critiques requises pour la soumission du rapport IA "RAPPORT_IMPLEMENTATION_SPRINT3-CLI-WATCH_2026-03-04.md" :
- Ajout de l'auteur humain responsable dans le rapport
- Insertion d'une traçabilité PR (placeholder à remplacer par l'URL réelle)
- Ajout du fichier `PATCH_MANIFEST.md` listant les fichiers modifiés

Ce patch ne modifie pas le code métier ; seuls des fichiers de documentation et de manifeste sont ajoutés/modifiés.

Checklist (obligatoire — cocher les éléments complétés avant merge)

- [ ] Rapport conforme au pattern `RAPPORT_<TYPE>_YYYY-MM-DD.md`
- [ ] Placé dans `docs/ia/rapports-execution/`
- [ ] Basé sur `docs/ia/templates/rapport_template.md`
- [x] Mention "Généré par IA" + outil/agent (GitHub Copilot)
- [ ] Au moins 1 reviewer humain assigné (demande : @<nom_reviewer>)
- [ ] PATCH_MANIFEST.md présent et listant les fichiers modifiés

Actions à effectuer après création de la PR

1. Remplacer `<PR_URL>` et `<Nom humain responsable>` dans `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_SPRINT3-CLI-WATCH_2026-03-04.md` par l'URL de la PR et le nom du submitter.
2. Assigner un reviewer humain : `@<nom_reviewer>` (recommande : @team-architecture).
3. Attendre revue humaine et corriger les commentaires éventuels.

Contexte et justification

Ce changement est nécessaire pour satisfaire la politique centralisée `docs/ia/instructions/reports-docs.instructions.md` qui impose un auteur humain responsable, une traçabilité PR explicite et la présence d'un manifeste de patch.

Contact

Pour questions, taguer `@team-architecture`.

