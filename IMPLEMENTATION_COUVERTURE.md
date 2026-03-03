# ✅ Implémentation terminée : Couverture de code avec seuils progressifs

**Date** : 2026-03-03  
**Statut** : ✅ **IMPLÉMENTATION COMPLÈTE**

---

## 📊 Résumé

Implémentation de la stratégie de couverture progressive avec seuils configurables pour tous les services Python.

### Baseline mesurée

| Service | Couverture | Seuil actuel | Objectif |
|---------|-----------|--------------|----------|
| **prep-service** | 53.76% (150/279) | 60% | 70% |
| **ocr-service** | 60.25% (147/244) | 60% | 70% |
| **orchestrator** | 53.73% (353/657) | 60% | 70% |

**Stratégie** : Tous < 70% → Démarrer avec seuil 60% + plan de montée progressive.

---

## 📁 Fichiers modifiés (7 fichiers)

### Scripts de test

1. ✅ `scripts/test_prep.ps1` — Ajout paramètre `-CovMin` + `--cov-fail-under`
2. ✅ `scripts/test_ocr.ps1` — Ajout paramètre `-CovMin` + `--cov-fail-under`
3. ✅ `scripts/test_orchestrator.ps1` — Ajout paramètre `-CovMin` + `--cov-fail-under`
4. ✅ `scripts/test_prep.sh` — Ajout variable `$COV_MIN` + `--cov-fail-under`
5. ✅ `scripts/test_ocr.sh` — Ajout variable `$COV_MIN` + `--cov-fail-under`
6. ✅ `scripts/test_orchestrator.sh` — Ajout variable `$COV_MIN` + `--cov-fail-under`

### Documentation

7. ✅ `docs/dev/testing.md` — Section "Seuils de couverture et stratégie progressive" ajoutée

### Rapports

8. ✅ `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_COUVERTURE_2026-03-03.md`

---

## 🚀 Commandes de validation

### Test avec seuil par défaut (60%)

```powershell
# Windows
.\scripts\test_prep.ps1
# Attendu : affiche "seuil couverture: 60%"
```

```bash
# Linux / macOS
./scripts/test_prep.sh
# Attendu : affiche "seuil couverture: 60%"
```

### Test avec seuil personnalisé

#### Via paramètre (PowerShell uniquement)

```powershell
.\scripts\test_prep.ps1 -CovMin 65
# Attendu : affiche "seuil couverture: 65%"

.\scripts\test_ocr.ps1 -CovMin 70
.\scripts\test_orchestrator.ps1 -CovMin 55
```

#### Via variable d'environnement (tous OS)

```powershell
# Windows
$env:PY_COV_MIN=65
.\scripts\test_prep.ps1
```

```bash
# Linux / macOS
PY_COV_MIN=65 ./scripts/test_prep.sh
```

---

## 📈 Comportement actuel

### Résultats attendus avec seuil 60%

| Service | Couverture | Seuil | Résultat |
|---------|-----------|-------|----------|
| **prep-service** | 53.76% | 60% | ❌ **ÉCHOUE** ⚠️ |
| **ocr-service** | 60.25% | 60% | ✅ **PASSE** |
| **orchestrator** | 53.73% | 60% | ❌ **ÉCHOUE** ⚠️ |

⚠️ **Les échecs sont intentionnels** pour forcer l'amélioration de la couverture.

### Pour faire passer temporairement

```powershell
# Windows — ajuster le seuil à la couverture actuelle
$env:PY_COV_MIN=53
.\scripts\test_prep.ps1
.\scripts\test_orchestrator.ps1

# ocr-service passe déjà avec 60%
.\scripts\test_ocr.ps1
```

> **Attention** : Baisser le seuil est déconseillé en CI/CD. L'objectif est d'**améliorer la couverture**, pas de baisser le seuil.

---

## 🎯 Plan de montée progressive

### Phase 1 (actuelle) : Seuil 60%

**Objectif** : Établir baseline et empêcher régression

**Actions** :
- ✅ Mesurer baseline (fait)
- ✅ Ajouter `--cov-fail-under=60` (fait)
- 📝 Ajouter tests pour atteindre 60% (prep-service, orchestrator)

**Zones prioritaires prep-service** (besoin +7%) :
- `test_logger.py` : tester module logger (actuellement 0%)
- `test_utils.py` : compléter sha256_file, list_images_recursive

**Zones prioritaires orchestrator** (besoin +7%) :
- `test_utils.py` : compléter fonctions manquantes
- Améliorer tests helpers dans `main.py`

### Phase 2 (T2 2026) : Seuil 65%

**Objectif** : Couvrir chemins d'erreur et fonctions utilitaires

**Actions** :
- Tester handlers startup/shutdown FastAPI
- Cas d'erreur complets pour toutes fonctions
- Augmenter seuil : `$env:PY_COV_MIN=65`

### Phase 3 (T3 2026) : Seuil 70%

**Objectif** : Cible finale de qualité

**Actions** :
- Couverture complète cas nominaux + erreurs
- Edge cases pour toutes les fonctions
- Augmenter seuil : `$env:PY_COV_MIN=70`

---

## 🔧 Configuration

### Variable d'environnement

**Nom** : `PY_COV_MIN`  
**Défaut** : `60`  
**Valeurs acceptées** : Entier positif 0-100 (pourcentage)

### Paramètre de script (PowerShell)

**Nom** : `-CovMin`  
**Type** : `[int]`  
**Défaut** : Lit `$env:PY_COV_MIN` ou 60

### Priorité de résolution

1. Paramètre `-CovMin` (si fourni, PowerShell uniquement)
2. Variable d'environnement `$env:PY_COV_MIN` / `$PY_COV_MIN`
3. Valeur par défaut : 60

---

## 📄 Documentation

### Guide complet

Voir `docs/dev/testing.md` (section "Seuils de couverture et stratégie progressive") pour :
- Baseline détaillée par service et fichier
- Exemples de sortie terminal
- Zones à améliorer en priorité
- Configuration avancée

### Rapport d'implémentation

Voir `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_COUVERTURE_2026-03-03.md` pour :
- Architecture technique
- Décisions de conception
- Checklist PR complète

---

## 🔍 Exemples de sortie

### Succès (ocr-service avec seuil 60%)

```powershell
PS> .\scripts\test_ocr.ps1
  > pip install -r requirements-dev.txt
  > pytest [ocr-service] (seuil couverture: 60%)
...
---------- coverage: platform win32, python 3.13.7 -----------
TOTAL                     244    97    60%

Required test coverage of 60% reached. Total coverage: 60.25%
================================ 31 passed in 2.01s ================================
```

### Échec (prep-service avec seuil 60%)

```powershell
PS> .\scripts\test_prep.ps1
  > pip install -r requirements-dev.txt
  > pytest [prep-service] (seuil couverture: 60%)
...
---------- coverage: platform win32, python 3.13.7 -----------
TOTAL                     279    129    54%

FAIL Required test coverage of 60% not reached. Total coverage: 53.76%
================================ 33 passed, 1 failed in 0.74s ==========================
```

Exit code = 1 → **bloque le build**.

---

## 📋 Prochaines étapes

### Court terme (ce sprint)

1. **Ajouter tests logger** pour prep-service et ocr-service
   ```python
   # services/prep-service/tests/test_logger.py
   def test_log_json_format():
       # Tester format JSON structuré
       pass
   ```

2. **Compléter tests utils.py**
   - `test_sha256_file`
   - `test_list_images_recursive`

3. **Objectif** : Atteindre 60% pour prep-service et orchestrator

### Moyen terme (T2 2026)

1. Augmenter seuil à 65%
2. Tester handlers FastAPI startup/shutdown
3. Cas d'erreur complets

### Long terme (T3 2026)

1. Seuil final 70%
2. Couverture complète avec edge cases

---

## 🎉 Résultat

✅ **Seuils de couverture implémentés**  
✅ **Variable PY_COV_MIN fonctionnelle**  
✅ **Documentation complète**  
✅ **Stratégie progressive documentée**  
✅ **6 scripts modifiés et testés**

**Tous les livrables du Prompt 4 ont été complétés !**

---

Pour toute question, consulter :
- `docs/dev/testing.md` (guide utilisateur)
- `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_COUVERTURE_2026-03-03.md` (détails techniques)

