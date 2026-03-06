# Politique de sécurité des dépendances — comic2pdf-app

> **Date** : 2026-03-06
> **Équipe** : comic2pdf-app

---

## 1. Politique d'audit de vulnérabilités

### Outils

| Outil | Périmètre | Workflow |
|---|---|---|
| `pip-audit` (Python) | Services Python + tools — CVEs PyPI/OSV | `dependency-audit.yml` (Job A) |
| OWASP Dependency-Check (Java) | `desktop-app` Maven — CVEs NVD | `ci.yml` (job `java-audit`) |

### Fréquence et déclencheurs

| Déclencheur | Mode | Comportement |
|---|---|---|
| `pull_request` → `main` | **BLOQUANT** | Fail si CVE HIGH ou CRITICAL (CVSS ≥ 7) |
| `push` → `main` | **BLOQUANT** | Idem |
| `schedule` (lundi 06:00 UTC) | **WARN-ONLY** | `continue-on-error: true` + job summary + artefact JSON |

### Seuil de fail

- **HIGH** (CVSS 7.0–8.9) et **CRITICAL** (CVSS 9.0–10.0) → fail bloquant en PR/push.
- **MEDIUM**, **LOW**, **INFORMATIONAL** → non bloquants (reporting uniquement).

### Comment déclencher un audit manuel

```bash
# Localement (depuis le dossier du service)
cd services/prep-service
pip install pip-audit
pip install -r requirements.txt        # installer les deps pour couvrir les transitives
python -m pip_audit --severity high    # fail si HIGH/CRITICAL
```

### Comment lire un rapport JSON pip-audit

```json
{
  "dependencies": [
    {
      "name": "somepackage",
      "version": "1.0.0",
      "vulns": [
        {
          "id": "PYSEC-2024-XXXX",
          "fix_versions": ["1.0.1"],
          "aliases": ["CVE-2024-XXXXX"],
          "description": "..."
        }
      ]
    }
  ]
}
```

- `dependencies[].vulns` vide = aucune vulnérabilité détectée pour ce paquet.
- `fix_versions` = versions qui corrigent la CVE → mettre à jour vers la plus basse disponible.
- Les artefacts JSON des runs schedule sont disponibles dans GitHub Actions → onglet **Artifacts**
  (rétention 30 jours), nommés `pip-audit-<service>-schedule`.

### Note sur les versions non épinglées

> Jusqu'à la PR `chore/pin-dependencies` (pip-tools), l'audit CI installe les
> **dernières versions disponibles** de chaque paquet (pas de version fixe connue).
> L'audit est donc un **"meilleur cas"** : il peut manquer des CVEs sur des versions
> antérieures effectivement déployées si l'environnement local diverge du CI.
>
> Après `chore/pin-dependencies`, le `requirements.txt` contiendra des versions épinglées
> issues de `pip-compile` → l'audit CI portera sur les **versions réellement déployées**
> (arbre transitif résolu, reproductible).

### Coexistence avec `ci.yml`

Les jobs `python-audit` et `java-audit` dans `ci.yml` sont conservés en mode **reporting**
(non bloquants, artefacts JSON). Le gating HIGH/CRITICAL est assuré par `dependency-audit.yml`.

**Plan de sortie** : supprimer/refactorer `python-audit` dans `ci.yml` en workflow réutilisable
après 1–2 cycles de stabilisation de `dependency-audit.yml`.

---

## 2. Ghostscript (AGPL-3.0) — Décision de conformité

### Statut : ✅ Option A — Conserver avec conformité documentée

#### Justification technique

| Point | Détail |
|---|---|
| **Usage** | Ghostscript (`gs`) est une dépendance **système transitive** d'`ocrmypdf` |
| **Périmètre** | Uniquement dans l'image Docker `ocr-service` (Dockerfile `apt-get install ghostscript`) |
| **Services non concernés** | `prep-service`, `orchestrator`, `tools`, `desktop-app` — pas de Ghostscript |
| **Mode de distribution** | Pas de redistribution de Ghostscript en binaire standalone propre au projet |
| **Obligations AGPL** | Documentées dans [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) |

#### Obligations AGPL-3.0 (résumé opérationnel)

L'AGPL-3.0 déclenche des obligations de publication du code source si :

1. **Distribution d'un binaire** : l'image Docker `ocr-service` est distribuée à des tiers.
2. **Service réseau** : le service est exposé à des utilisateurs via un réseau (SaaS).

Dans le cas actuel (`comic2pdf-app` usage interne / open-source MIT) :
- Le code source est déjà public → obligation de publication satisfaite.
- En cas de distribution commerciale ou SaaS : **consulter un conseiller juridique**.

> **Référence complète** : [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) —
> section "Ghostscript (AGPL-3.0) — Point critique".

#### Décision

**Conserver Ghostscript** tant que `ocrmypdf` en dépend et qu'aucune alternative
couvrant l'intégralité des fonctionnalités n'est disponible sans patch/fork.
Documenter et surveiller. Réévaluer si obligation de distribution commerciale détectée.

---

## 3. Next steps — Ticket de migration Ghostscript

### Issue à créer : `feat/ghostscript-alternative`

**Objectif** : évaluer un remplacement de Ghostscript par une alternative sous licence permissive.

| Candidat | Licence | Couvre les besoins OCRmyPDF ? | Notes |
|---|---|---|---|
| `pikepdf` (libqpdf) | MIT / Apache-2.0 | Partiellement | Manipulation PDF, pas rasterization complète |
| `pypdf` | BSD-3-Clause | Non | Pas de rendu/rasterization |
| Patch `ocrmypdf` sans `gs` | — | À évaluer | Niveau effort : élevé (fork ou PR upstream) |

**Critère de bascule** : obligation de distribution commerciale détectée **OU** adoption
d'une PR upstream `ocrmypdf` supprimant la dépendance `gs`.

**Effort estimé** : élevé (patch/fork `ocrmypdf`). Ne pas engager sans besoin business avéré.

**Action immédiate** : ouvrir l'issue `feat/ghostscript-alternative` avec ce tableau
comme point de départ, sans bloquer la roadmap actuelle.

---

## 4. Dependabot & pinning des dépendances

### Configuration Dependabot

Fichier : [`.github/dependabot.yml`](../../.github/dependabot.yml)

| Cible | Écosystème | Schedule | Groupe |
|---|---|---|---|
| `services/prep-service` | pip | Weekly | patch-minor |
| `services/ocr-service` | pip | Weekly | patch-minor |
| `services/orchestrator` | pip | Weekly | patch-minor |
| `tools` | pip | Weekly | patch-minor |
| `/` (workflows) | github-actions | Weekly | patch-minor |

### Comportement actuel (sans pinning)

> ⚠️ **Dependabot pip est quasi-décoratif sans versions épinglées.**
>
> Sans `==x.y.z` dans les `requirements.txt`, Dependabot ne connaît pas la version
> de départ et ne peut pas proposer de PR de mise à jour pip.
> Les entrées `github-actions` fonctionnent normalement (versions dans `uses: action@vX`).

### Merge des PRs Dependabot

Les PRs Dependabot sont mergées **manuellement** après revue humaine.
Il n'y a pas d'auto-merge configuré sur ce dépôt.

### Prochaine PR obligatoire : `chore/pin-dependencies`

**Objectif** : introduire `pip-tools` pour les 4 cibles Python.

```
requirements.in   (sources — liste des deps directes, gérée par les développeurs)
      ↓  pip-compile
requirements.txt  (généré — versions épinglées, arbre transitif résolu)
```

**Impact après pinning** :
- Dependabot pip propose des PRs de mise à jour réelles (version connue → nouvelle version).
- L'audit CI porte sur les versions réellement déployées (reproductible).
- L'artefact `python-licenses-<service>` est reproductible à versions fixes.

**Priorité** : à créer **immédiatement après merge** de la PR de sécurité/CI (`chore/security-compliance-2026-03-06`).

---

## 5. Références

| Document | Lien |
|---|---|
| Notices licences tierces (Ghostscript, 7z, etc.) | [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) |
| Snapshot licences Python runtime | [`docs/compliance/python-deps-licenses.md`](../compliance/python-deps-licenses.md) |
| Workflow audit CI | [`.github/workflows/dependency-audit.yml`](../../.github/workflows/dependency-audit.yml) |
| Configuration Dependabot | [`.github/dependabot.yml`](../../.github/dependabot.yml) |

---

*Ce document ne constitue pas un avis juridique.
Pour des questions de conformité de distribution, consulter un spécialiste en droit des licences logicielles.*
*Pour toute question, ouvrir une issue et taguer `@team-architecture`.*



