---
applyTo: '**'
description: 'Politique centralisée — organisation des rapports et documentation générés par l\'IA (emplacements, nommage, template, exceptions, checklist)'
---

# Instructions — Organisation des rapports et documentation générés par l'IA

Version: 1.1.0
Date: 2026-02-28
Auteur: Équipe comic2pdf-app

Objectif
--------
Figer et centraliser la politique d'organisation des rapports et documents produits par des outils ou agents IA afin d'éviter la pollution du dépôt GitHub et de maintenir une séparation claire entre documentation utilisateur et rapports techniques/IA.

Champ d'application
--------------------
- S'applique à tous les artefacts (rapports, analyses, rapports d'implémentation, rapports de migration, etc.) générés par des agents/assistants/IA et ajoutés au dépôt.
- Ne s'applique pas aux documents utilisateur finaux maintenus explicitement par des développeurs humains (ex : `README.md`, guides officiels) sauf si générés automatiquement par un agent IA.

Règles principales (normatives)
-------------------------------
1. Emplacements autorisés
   - `docs/ia/` : emplacement principal pour les rapports techniques/analyses produits par l'IA.
     - **IMPORTANT** : Les rapports doivent être organisés dans des sous-dossiers, **PAS à la racine de docs/ia/**
     - `docs/ia/rapports-execution/` : rapports d'implémentation, d'exécution de features, POC
     - `docs/ia/rapports-migration/` : rapports liés aux migrations ou modifications de schéma
     - `docs/ia/prompts/` : prompts et spécifications conservés
     - `docs/ia/templates/` : templates officiels de rapports

2. Pattern de nommage obligatoire
   - Tout rapport IA doit être nommé selon le pattern : `RAPPORT_<TYPE>_YYYY-MM-DD.md`
   - `<TYPE>` en majuscules, sans espaces (ex : `IMPLEMENTATION`, `ANALYSE`, `MIGRATION`, `SECURITE`)
   - Date au format ISO `YYYY-MM-DD` (ex : `RAPPORT_IMPLEMENTATION_2026-02-28.md`)

3. Template
   - Le template officiel est : `docs/ia/templates/rapport_template.md`.
   - Utiliser ce template comme base et remplir toutes les sections obligatoires avant soumission.

4. Checklist minimale (doit apparaître dans chaque rapport)
   - Titre et type du rapport
   - Date (YYYY-MM-DD)
   - Auteur(s) / équipe
   - Contexte et résumé (2–4 phrases)
   - Description des changements ou des résultats (liste synthétique)
   - Étapes pour reproduire / commandes exécutées
   - Fichiers modifiés / chemins pertinents
   - Liens vers PR / issues
   - Contact pour questions

5. **INTERDIT : Rapports à la racine de docs/ia/**
   - ❌ **Aucun rapport `RAPPORT_*.md` ne doit être placé directement dans `docs/ia/`**
   - ✅ Utiliser obligatoirement un sous-dossier : `docs/ia/rapports-execution/` ou `docs/ia/rapports-migration/`
   - Exception : fichiers non-rapports peuvent rester à la racine de `docs/ia/` si justifiés

6. Exigences de publication
   - Toute PR qui ajoute ou modifie un rapport IA doit :
     - Respecter l'emplacement et le pattern de nommage ci-dessus (sous-dossier obligatoire)
     - Inclure au moins 1 reviewer humain explicitement demandé
     - Indiquer dans le rapport la mention `"Généré par IA"` ainsi que l'agent/outil utilisé (ex : `Copilot`)

7. Exceptions
   - Toute exception doit être demandée via PR (body) avec justification technique et approuvée par au moins 1 reviewer humain.

8. Procédure de correction (manuelle)
   - Si un rapport est ajouté au mauvais emplacement :
     1. Ouvrir une PR de correction (branch `fix/move-rapport-<id>`)
     2. Déplacer/renommer le fichier vers `docs/ia/rapports-execution/` ou `docs/ia/rapports-migration/`
     3. Indiquer dans le body de la PR la raison de la correction et référencer la PR originale
   - Exemples PowerShell :
     - Déplacer un rapport d'implémentation mal placé :
       ```powershell
       git checkout -b fix/move-rapport-implementation ;
       git mv docs/ia/RAPPORT_IMPLEMENTATION_2026-02-28.md docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_2026-02-28.md ;
       git commit -m "fix: déplacer rapport implémentation vers rapports-execution/" ;
       git push origin HEAD
       ```
     - Déplacer un rapport de migration mal placé :
       ```powershell
       git checkout -b fix/move-rapport-migration ;
       git mv docs/ia/RAPPORT_MIGRATION_2026-02-28.md docs/ia/rapports-migration/RAPPORT_MIGRATION_2026-02-28.md ;
       git commit -m "fix: déplacer rapport migration vers rapports-migration/" ;
       git push origin HEAD
       ```

9. Procédure d'exception
   - Pour demander une exception, ouvrir une PR et inclure une section `Exception-Request` dans le body expliquant : raison, durée (temporaire/permanent), impact, et reviewer attendu. L'exception n'est valide qu'après approbation explicite d'au moins 1 reviewer humain.

10. Non-répudiation et traçabilité
    - Tous les rapports IA doivent mentionner l'auteur humain responsable de la submission (même si contenu généré par IA).

11. Liens et références
    - Template officiel : `docs/ia/templates/rapport_template.md`
    - Politique centralisée : `.github/instructions/reports-docs.instructions.md` (ce fichier)

Annexe — Checklist PR (à inclure dans le message de PR lorsqu'un rapport IA est ajouté)
--------------------------------------------------------------------------------------
- [ ] Rapport conforme au pattern `RAPPORT_<TYPE>_YYYY-MM-DD.md`
- [ ] Placé dans `docs/ia/rapports-execution/` ou `docs/ia/rapports-migration/`
- [ ] Basé sur `docs/ia/templates/rapport_template.md`
- [ ] Au moins 1 reviewer humain assigné
- [ ] Mention "Généré par IA" + outil/agent
- [ ] Sections minimales complètes (titre, date, auteur, résumé, étapes, fichiers modifiés, liens PR)

Contact
-------
Pour des questions sur cette politique, ouvrir une issue dans le dépôt et taguer `@team-architecture`.
