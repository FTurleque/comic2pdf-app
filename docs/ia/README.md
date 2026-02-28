# docs/ia — Documentation générée par IA

Ce dossier centralise tous les artefacts produits par des agents ou assistants IA dans le cadre du projet `comic2pdf-app`.

## Structure

```
docs/ia/
├── rapports-execution/   # Rapports d'implémentation de features, POC, exécutions
├── rapports-migration/   # Rapports de migration ou modification de schéma/config
├── prompts/              # Prompts et spécifications conservés pour traçabilité
└── templates/
    └── rapport_template.md   # Template officiel de rapport IA
```

## Règles

- **Nommage** : `RAPPORT_<TYPE>_YYYY-MM-DD.md` (ex : `RAPPORT_IMPLEMENTATION_2026-02-28.md`)
- **Emplacement** : toujours dans un sous-dossier, **jamais à la racine de `docs/ia/`**
- **Template** : utiliser `docs/ia/templates/rapport_template.md`
- **Mention obligatoire** : `"Généré par IA"` + outil utilisé dans chaque rapport

Politique complète : `.github/instructions/reports-docs.instructions.md`

