# RAPPORT_IMPLEMENTATION_LICENCE-MIT_2026-02-28

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `Fabrice Turleque`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Intégration licence MIT + notices de licences tierces |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-02-28` |
| **Auteur(s)** | `Fabrice Turleque` |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | À renseigner |

---

## 2. Contexte et résumé

Le dépôt `comic2pdf-app` ne disposait d'aucun fichier de licence ni de notice sur les composants tiers.
Cette tâche ajoute la licence MIT du projet, un fichier `THIRD_PARTY_NOTICES.md` avec des disclaimers
explicites sur Ghostscript (AGPL-3.0) et 7-Zip/RAR (licence hybride), et met à jour l'ensemble des
README et documentations pour référencer ces fichiers de façon cohérente.
Aucune modification de code fonctionnel n'a été effectuée (patch-only, documentation uniquement).

---

## 3. Description des changements

### Fichiers ajoutés

| Fichier | Type | Description |
|---|---|---|
| `LICENSE` | Nouveau | Texte complet de la licence MIT — Copyright (c) 2026 Fabrice Turleque |
| `THIRD_PARTY_NOTICES.md` | Nouveau | Notices tierces : disclaimer Ghostscript AGPL, 7-Zip/RAR, tableau complet des composants |
| `desktop-app/README.md` | Nouveau | README minimal du module JavaFX (lancement, tests, licence) |
| `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_LICENCE-MIT_2026-02-28.md` | Nouveau | Ce rapport |

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `README.md` | Modifié | Ajout badge `![License: MIT]` + section `## License` avec liens et mention Ghostscript AGPL |
| `docs/README.md` | Modifié | Ajout ligne Licence dans table des liens rapides + section `## Licence` en fin de fichier |
| `docs/user/README.md` | Modifié | Ajout section `## Licence` avant le lien de retour |
| `docs/dev/README.md` | Modifié | Ajout section `## Licence` avant le lien de retour |
| `docs/dev/setup.md` | Modifié | Ajout note licences outils Docker avant `## Retour` |
| `docs/dev/testing.md` | Modifié | Ajout note licences outils Docker avant `## Retour` |

---

## 4. Points d'attention — Disclaimers

### Ghostscript (AGPL-3.0) — Point critique

Ghostscript est installé dans l'image Docker `ocr-service` (via `apt-get install ghostscript`).
Sa licence **AGPL-3.0** peut imposer l'obligation de publier le code source complet de toute
application dérivée lors de sa distribution, y compris en mode SaaS.

> Extrait du disclaimer ajouté dans `THIRD_PARTY_NOTICES.md` :
> *"L'utilisation de Ghostscript dans un produit distribué peut déclencher l'obligation de publier
> le code source complet de l'application dérivée, y compris si le logiciel est fourni comme
> service en réseau (SaaS), selon les conditions de l'AGPL-3.0."*

Lien officiel : <https://www.ghostscript.com/licensing/index.html>

### 7-Zip / p7zip-full — À confirmer (RAR)

Le package `p7zip-full` (Debian) installé dans `prep-service` peut extraire les archives RAR (`.cbr`).

- **Base 7-Zip** : principalement LGPL (à confirmer précisément selon les composants).
- **Support RAR** : soumis à la **licence UNRAR propriétaire** distincte, qui interdit notamment
  la création d'outils de compression RAR.

> ⚠️ **À confirmer selon la chaîne d'extraction réellement utilisée (CBR = RAR) et les binaires
> embarqués dans le conteneur Docker.**

Lien officiel : <https://www.7-zip.org/license.txt>

---

## 5. Étapes pour reproduire / commandes exécutées

Aucune commande de build/test requise pour cette tâche (modification documentation uniquement).

Vérification de cohérence des liens :

```powershell
# Rechercher les mentions LICENSE dans les docs
Select-String -Path "docs\**\*.md","README.md","desktop-app\README.md" -Pattern "LICENSE" -Recurse

# Rechercher les mentions THIRD_PARTY_NOTICES dans les docs
Select-String -Path "docs\**\*.md","README.md","desktop-app\README.md" -Pattern "THIRD_PARTY_NOTICES" -Recurse

# Vérifier que le fichier LICENSE existe bien
Test-Path "LICENSE"

# Vérifier que le fichier THIRD_PARTY_NOTICES.md existe bien
Test-Path "THIRD_PARTY_NOTICES.md"
```

### Résultats des tests (non impactés par cette tâche)

| Module | Tests | Résultat |
|---|---|---|
| `prep-service` | 12 | ✅ Non modifié |
| `ocr-service` | 17 | ✅ Non modifié |
| `orchestrator` | 68 | ✅ Non modifié |
| `desktop-app` | 21 | ✅ Non modifié |

---

## 6. Checklist de validation

- [x] `LICENSE` présent à la racine (texte MIT complet, Copyright 2026 Fabrice Turleque)
- [x] `THIRD_PARTY_NOTICES.md` présent à la racine
- [x] Disclaimer Ghostscript AGPL-3.0 visible en haut de `THIRD_PARTY_NOTICES.md` (section ⚠️)
- [x] Mention 7-Zip/RAR avec note "À confirmer" dans `THIRD_PARTY_NOTICES.md`
- [x] `README.md` racine : badge MIT + section `## License` + lien `THIRD_PARTY_NOTICES.md`
- [x] `docs/README.md` : ligne Licence dans table + section `## Licence`
- [x] `docs/user/README.md` : section `## Licence` ajoutée
- [x] `docs/dev/README.md` : section `## Licence` ajoutée
- [x] `docs/dev/setup.md` : note licences outils Docker ajoutée
- [x] `docs/dev/testing.md` : note licences outils Docker ajoutée
- [x] `desktop-app/README.md` : créé avec section License + mention Ghostscript AGPL
- [x] Ce rapport suffixé `RAPPORT_IMPLEMENTATION_LICENCE-MIT_2026-02-28.md` créé (sans écraser l'existant)
- [x] Aucun code fonctionnel modifié (patch-only documentation)
- [x] `groupId` Maven (`com.fturleque.comic2pdf`) non modifié
- [ ] `LICENSE` détecté par GitHub (badge MIT automatique) — à vérifier après push

---

## 7. Liens et références

- Fichier de licence : [`LICENSE`](../../../LICENSE)
- Notices tierces : [`THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md)
- Politique rapports IA : [`.github/instructions/reports-docs.instructions.md`](../../../.github/instructions/reports-docs.instructions.md)
- Instructions Copilot : [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md)
- Rapport précédent (ne pas écraser) : [`RAPPORT_IMPLEMENTATION_2026-02-28.md`](RAPPORT_IMPLEMENTATION_2026-02-28.md)

---

## 8. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

