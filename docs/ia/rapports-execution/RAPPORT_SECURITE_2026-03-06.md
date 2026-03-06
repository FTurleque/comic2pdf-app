# RAPPORT_SECURITE_2026-03-06

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `Équipe comic2pdf-app — <à compléter : Prénom NOM — identifiant GitHub>`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Sécurité et conformité des dépendances — Audit CI, Dependabot, licences |
| **Type** | `SECURITE` |
| **Date** | `2026-03-06` |
| **Auteur(s)** | Équipe comic2pdf-app |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | `#[numéro à compléter]` — `[lien à compléter]` |

---

## 2. Contexte et résumé

Ce rapport documente la mise en place d'une infrastructure DevSecOps complète pour
`comic2pdf-app` : audit automatisé des vulnérabilités Python (pip-audit) en CI avec
politique de fail explicite (HIGH/CRITICAL bloquant en PR/push, warn-only en schedule),
configuration Dependabot pour les mises à jour automatisées de dépendances pip et
github-actions, documentation de la conformité licences (décision Ghostscript AGPL-3.0
Option A : conserver + documenter), et snapshot versionné des licences runtime Python.

L'objectif est de réduire le MTTR sécurité, de bloquer l'introduction de CVEs HIGH/CRITICAL
en PR, et de fournir une traçabilité complète des licences tiers sans perturber les
workflows existants (`ci.yml` conservé en mode reporting parallèle).

---

## 3. Description des changements

### Fichiers créés / modifiés

| Fichier | Type | Description de la modification |
|---|---|---|
| `.github/dependabot.yml` | **Nouveau** | Configuration Dependabot pip (4 cibles) + github-actions. Schedule weekly, groupes patch-minor. Commentaire sur prérequis pinning. |
| `.github/workflows/dependency-audit.yml` | **Nouveau** | Workflow dédié : Job A `pip-audit-gating` (bloquant PR/push, warn schedule) + Job B `licenses-snapshot` (non bloquant, artefact 30j). |
| `docs/compliance/python-deps-licenses.md` | **Nouveau** | Snapshot versionné des licences runtime directes Python (4 services). Dossier `docs/compliance/` créé. |
| `docs/security/dependencies.md` | **Nouveau** | Politique d'audit complète, décision Ghostscript AGPL Option A, ticket migration, Dependabot & pinning. Dossier `docs/security/` créé. |
| `.github/workflows/ci.yml` | **Modifié** | Commentaires de coexistence ajoutés sur `python-audit` et `java-audit` (REPORTING UNIQUEMENT + plan de sortie). |
| `docs/ia/rapports-execution/RAPPORT_SECURITE_2026-03-06.md` | **Nouveau** | Ce rapport. |
| `PATCH_MANIFEST.md` | **Modifié** | Nouvelle entrée branche `chore/security-compliance-2026-03-06`. |

### Décisions techniques cristallisées

| Point | Décision |
|---|---|
| Appel pip-audit | `python -m pip_audit --severity high` (module Python, pas PATH) |
| Arbre transitif | `pip install -r requirements.txt` avant audit = transitives couvertes |
| Bascule schedule/PR | `if: github.event_name != 'schedule'` bloquant ; `continue-on-error: true` warn en schedule |
| Ghostscript | **Option A** — conserver + documenter (dépendance transitive `ocrmypdf`, non redistribuée en binaire standalone) |
| Dependabot pip | Décoratif jusqu'à `chore/pin-dependencies` — documenté explicitement |
| Auto-merge | Patch/minor uniquement ; prérequis GitHub *Allow auto-merge* documenté |
| `pip-licenses` snapshot | Runtime-only dans `docs/compliance/` ; artefact CI = complet (directes + transitives) |
| `ci.yml` | Conservé en mode reporting parallèle — plan de sortie en commentaire |

---

## 4. Étapes pour reproduire / commandes exécutées

### Déclencher l'audit manuellement (local)

```bash
# Depuis un service Python
cd services/prep-service
pip install pip-audit
pip install -r requirements.txt          # couvre les transitives
python -m pip_audit --severity high      # fail si CVE HIGH/CRITICAL
```

### Déclencher le workflow CI manuellement

```
GitHub Actions → Dependency Audit → Run workflow (branch: main)
```

### Vérifier Dependabot

```
GitHub → Insights → Dependency graph → Dependabot
```

### Générer le snapshot licences localement

```bash
cd services/ocr-service
pip install pip-licenses
pip install -r requirements.txt
pip-licenses --format=markdown --with-urls
```

### Résultats des tests (non impacté par cette PR)

| Module | Tests | Résultat |
|---|---|---|
| `prep-service` | — | ✅ Non modifié |
| `ocr-service` | — | ✅ Non modifié |
| `orchestrator` | — | ✅ Non modifié |
| `desktop-app` | — | ✅ Non modifié |

---

## 5. Points d'attention / Limitations

- **Dependabot pip décoratif** jusqu'à la PR `chore/pin-dependencies` (pip-tools) :
  sans versions épinglées, Dependabot ne peut pas proposer de PRs de mise à jour pip.
  **Action immédiate** : créer cette PR après merge de la présente PR.
- **Prérequis GitHub auto-merge** : activer *Settings → General → Pull Requests → Allow auto-merge*
  sans quoi `gh pr merge --auto` échoue silencieusement.
- **Ghostscript alternatives** : `pikepdf` ne couvre pas l'intégralité des besoins d'`ocrmypdf`.
  Un remplacement = patch/fork niveau effort élevé. Issue `feat/ghostscript-alternative` à créer.
- **`python-audit` dans `ci.yml`** : conservé en mode reporting. À supprimer/refactorer
  après 1–2 cycles de stabilisation de `dependency-audit.yml`.

---

## 6. Liens et références

- PR : `[lien vers la PR — à compléter après création]`
- Issue Ghostscript migration : `[feat/ghostscript-alternative — à créer]`
- Politique d'audit : `docs/security/dependencies.md`
- Snapshot licences : `docs/compliance/python-deps-licenses.md`
- Notices tierces : `THIRD_PARTY_NOTICES.md`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`

---

## 7. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.


