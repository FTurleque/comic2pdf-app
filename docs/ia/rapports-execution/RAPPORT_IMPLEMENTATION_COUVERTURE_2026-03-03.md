# RAPPORT_IMPLEMENTATION_2026-03-03

> **Généré par IA** — Outil/Agent : `GitHub Copilot`
> **Auteur responsable** : `Assistant IA — Session 2026-03-03`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | Couverture de code avec seuils progressifs |
| **Type** | `IMPLEMENTATION` |
| **Date** | `2026-03-03` |
| **Auteur(s)** | `Assistant IA Copilot` |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | `À créer` |

---

## 2. Contexte et résumé

Implémentation de seuils de couverture progressifs pour les services Python avec la stratégie : mesurer baseline → appliquer seuil 60% → plan de montée vers 70%. Ajout de la variable d'environnement `PY_COV_MIN` et du paramètre `-CovMin` dans tous les scripts de test (PowerShell et Shell). Documentation complète de la stratégie progressive dans `docs/dev/testing.md`.

---

## 3. Description des changements

### Fichiers modifiés

| Fichier | Type | Description |
|---|---|---|
| `scripts/test_prep.ps1` | **Modifié** | Ajout paramètre `$CovMin` + `--cov-fail-under` + affichage seuil |
| `scripts/test_ocr.ps1` | **Modifié** | Ajout paramètre `$CovMin` + `--cov-fail-under` + affichage seuil |
| `scripts/test_orchestrator.ps1` | **Modifié** | Ajout paramètre `$CovMin` + `--cov-fail-under` + affichage seuil |
| `scripts/test_prep.sh` | **Modifié** | Ajout variable `$COV_MIN` + `--cov-fail-under` + affichage seuil |
| `scripts/test_ocr.sh` | **Modifié** | Ajout variable `$COV_MIN` + `--cov-fail-under` + affichage seuil |
| `scripts/test_orchestrator.sh` | **Modifié** | Ajout variable `$COV_MIN` + `--cov-fail-under` + affichage seuil |
| `docs/dev/testing.md` | **Modifié** | Section "Seuils de couverture et stratégie progressive" ajoutée |

### Baseline mesurée

| Service | Couverture actuelle | Lignes | Décision |
|---------|---------------------|--------|----------|
| **prep-service** | 53.76% | 150/279 | < 70% → Seuil 60% |
| **ocr-service** | 60.25% | 147/244 | < 70% → Seuil 60% |
| **orchestrator** | 53.73% | 353/657 | < 70% → Seuil 60% |

### Variable d'environnement ajoutée

| Variable | Services | Défaut | Description |
|---|---|---|---|
| `PY_COV_MIN` | prep, ocr, orchestrator | `60` | Seuil minimal de couverture de code (%) |

### Paramètre de script ajouté (PowerShell)

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `-CovMin` | `int` | `60` | Seuil minimal de couverture (%), lit `$env:PY_COV_MIN` si non spécifié |

---

## 4. Étapes pour reproduire / commandes exécutées

### Modifications appliquées

```powershell
# Édition des 6 scripts de test (3 PS1 + 3 SH)
# Ajout section complète dans docs/dev/testing.md
```

### Validation des scripts modifiés

```powershell
# Test avec seuil par défaut (60%)
cd N:\workspace-dev\comic2pdf-app
.\scripts\test_prep.ps1
# Attendu : affiche "seuil couverture: 60%"

# Test avec seuil personnalisé (paramètre)
.\scripts\test_ocr.ps1 -CovMin 65
# Attendu : affiche "seuil couverture: 65%"

# Test avec variable d'environnement
$env:PY_COV_MIN=70
.\scripts\test_orchestrator.ps1
# Attendu : affiche "seuil couverture: 70%"
```

### Résultats attendus

| Service | Couverture | Seuil 60% | Résultat attendu |
|---------|-----------|-----------|------------------|
| **prep-service** | 53.76% | 60% | ❌ **ÉCHOUE** (voulu, force amélioration) |
| **ocr-service** | 60.25% | 60% | ✅ **PASSE** |
| **orchestrator** | 53.73% | 60% | ❌ **ÉCHOUE** (voulu, force amélioration) |

> **Note** : Les échecs avec seuil 60% sont **intentionnels** pour forcer l'amélioration de la couverture.
> Pour faire passer temporairement : `$env:PY_COV_MIN=53`

---

## 5. Architecture technique

### Stratégie progressive

#### Phase 1 (actuelle) : Seuil 60%
- Objectif : Établir une baseline et empêcher la régression
- Mesures : 
  - prep-service : 53.76% → besoin de +7% pour passer
  - ocr-service : 60.25% → passe actuellement
  - orchestrator : 53.73% → besoin de +7% pour passer

#### Phase 2 (T2 2026) : Seuil 65%
- Objectif : Couvrir les chemins d'erreur et fonctions utilitaires
- Zones prioritaires :
  - `logger.py` (actuellement 0% sur prep/ocr)
  - `utils.py` (52-77% selon services)
  - Handlers startup/shutdown FastAPI

#### Phase 3 (T3 2026) : Seuil 70%
- Objectif : Cible finale de qualité
- Couverture complète cas nominaux + erreurs

### Configuration flexible

#### Méthode 1 : Variable d'environnement (recommandée)
```powershell
# Windows
$env:PY_COV_MIN=65
.\scripts\test_prep.ps1
```

```bash
# Linux / macOS
PY_COV_MIN=65 ./scripts/test_prep.sh
```

#### Méthode 2 : Paramètre de script (PowerShell uniquement)
```powershell
.\scripts\test_prep.ps1 -CovMin 65
.\scripts\test_ocr.ps1 -CovMin 70
```

#### Comportement par défaut
Si `PY_COV_MIN` non défini ET paramètre `-CovMin` non fourni : **60%**

### Affichage du seuil

Tous les scripts affichent maintenant le seuil appliqué :
```
> pytest [prep-service] (seuil couverture: 60%)
```

Permet de vérifier facilement la configuration active.

---

## 6. Zones à améliorer en priorité

### prep-service (53.76% → objectif 60%)

| Fichier | Couverture | Actions recommandées |
|---------|-----------|---------------------|
| `main.py` | 52.29% | Ajouter tests startup/shutdown, worker_loop edges |
| `utils.py` | 52.63% | Tester sha256_file, list_images_recursive |
| `logger.py` | 0% | Créer test_logger.py (format, niveaux) |

**Gain potentiel** : +10% avec tests logger et utils complets

### ocr-service (60.25% → objectif 65%)

| Fichier | Couverture | Actions recommandées |
|---------|-----------|---------------------|
| `main.py` | ~50% | Tester claim_one edge cases, requeue_running |
| `logger.py` | 0% | Créer test_logger.py |

**Gain potentiel** : +8% avec tests logger

### orchestrator (53.73% → objectif 60%)

| Fichier | Couverture | Actions recommandées |
|---------|-----------|---------------------|
| `main.py` | 23.94% | Normal (boucle principale non testable), améliorer helpers |
| `utils.py` | 77% | Compléter tests fonctions manquantes |

**Gain potentiel** : +7% avec utils complet

---

## 7. Exemples de sortie

### Succès avec couverture suffisante

```
---------- coverage: platform win32, python 3.13.7 -----------
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
app\__init__.py             0      0   100%
app\core.py                98     5    95%   45-52
app\main.py               210   105    50%   89-105, 138-174
app\utils.py               48    12    75%   28-31, 40-44
-----------------------------------------------------
TOTAL                     356    122    66%

Required test coverage of 60% reached. Total coverage: 66.29%
================================ 31 passed in 2.01s ================================
```

### Échec avec couverture insuffisante

```
---------- coverage: platform win32, python 3.13.7 -----------
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
app\__init__.py             0      0   100%
app\core.py               122     22    82%   45-52, 78-81, 115-120
app\main.py               131     63    52%   89-105, 138-174, 210-235
app\utils.py               19     9     53%   28-31, 40-44
app\logger.py              26    26     0%   1-26
-----------------------------------------------------
TOTAL                     279    129    54%

FAIL Required test coverage of 60% not reached. Total coverage: 53.76%
```

Exit code = 1 → **bloque le build** (voulu).

---

## 8. Points d'attention / Limitations

### ✅ Implémenté

- Seuils configurables via `PY_COV_MIN` et `-CovMin`
- Affichage du seuil dans tous les scripts
- Documentation complète de la stratégie progressive
- Baseline mesurée pour les 3 services
- Plan de montée documenté (60% → 65% → 70%)

### ⚠️ Comportement actuel

- **prep-service et orchestrator échouent** avec seuil 60% (intentionnel)
- Nécessite ajout de tests pour atteindre le seuil
- CI/CD devra ajuster temporairement le seuil ou ajouter les tests manquants

### 🔄 Prochaines étapes recommandées

1. **Court terme (Sprint actuel)**
   - Ajouter `test_logger.py` pour prep-service et ocr-service
   - Compléter tests `utils.py` (sha256_file, list_images_recursive)
   - Objectif : atteindre 60% pour prep-service et orchestrator

2. **Moyen terme (T2 2026)**
   - Augmenter seuil à 65%
   - Tester handlers startup/shutdown FastAPI
   - Cas d'erreur complets pour toutes les fonctions

3. **Long terme (T3 2026)**
   - Seuil final 70%
   - Couverture complète incluant edge cases

---

## 9. Checklist PR

- [x] Scripts PowerShell modifiés (3 fichiers)
- [x] Scripts Shell modifiés (3 fichiers)
- [x] Documentation mise à jour (`docs/dev/testing.md`)
- [x] Baseline mesurée et documentée
- [x] Stratégie progressive documentée (3 phases)
- [x] Variable `PY_COV_MIN` implémentée
- [x] Paramètre `-CovMin` ajouté (PowerShell)
- [x] Affichage du seuil dans les messages
- [x] Rapport conforme : `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_COUVERTURE_2026-03-03.md`
- [ ] Tests ajoutés pour atteindre 60% (prep-service, orchestrator) — **À faire**
- [ ] Au moins 1 reviewer humain assigné (lors création PR)

---

## 10. Liens et références

- **pytest-cov documentation** : https://pytest-cov.readthedocs.io/
- **Baseline coverage.xml** : `services/*/coverage.xml`
- **Documentation tests** : `docs/dev/testing.md`
- **Politique rapports IA** : `.github/instructions/reports-docs.instructions.md`
- **Template rapport** : `docs/ia/templates/rapport_template.md`

---

## 11. Contact

Pour questions sur cette implémentation, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

---

