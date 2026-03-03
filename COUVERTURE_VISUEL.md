# 📊 Couverture de code — Résumé visuel

Date : 2026-03-03

```
┌─────────────────────────────────────────────────────────────────┐
│                  COUVERTURE DE CODE — BASELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  prep-service:     ████████████░░░░░░░░░░ 53.76% (150/279)    │
│  Seuil actuel:     ████████████████████░░ 60% ← À ATTEINDRE   │
│  Seuil cible:      ██████████████████████████████░░ 70%        │
│                    └─────────────┬──────────────┘              │
│                                  ↓                              │
│                          Besoin de +17 lignes                   │
│                                                                 │
│  ocr-service:      ████████████████████░░ 60.25% (147/244) ✅  │
│  Seuil actuel:     ████████████████████░░ 60% ← PASSE         │
│  Seuil cible:      ██████████████████████████████░░ 70%        │
│                                                                 │
│  orchestrator:     ████████████░░░░░░░░░░ 53.73% (353/657)    │
│  Seuil actuel:     ████████████████████░░ 60% ← À ATTEINDRE   │
│  Seuil cible:      ██████████████████████████████░░ 70%        │
│                    └─────────────┬──────────────┘              │
│                                  ↓                              │
│                          Besoin de +41 lignes                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Stratégie progressive

```
Phase 1 (ACTUELLE)        Phase 2 (T2 2026)        Phase 3 (T3 2026)
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│              │         │              │         │              │
│  Seuil 60%   │  ────→  │  Seuil 65%   │  ────→  │  Seuil 70%   │
│              │         │              │         │              │
│  Baseline    │         │  Chemins     │         │  Couverture  │
│  établie     │         │  d'erreur    │         │  complète    │
│              │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
     |                        |                        |
     v                        v                        v
 ❌ prep: 53.76%          + Tests utils           Edge cases
 ✅ ocr:  60.25%          + Tests logger          complets
 ❌ orch: 53.73%          + Handlers FastAPI      
```

## 🔧 Configuration

### Variable d'environnement

```powershell
# Windows
$env:PY_COV_MIN = 65
.\scripts\test_prep.ps1
```

```bash
# Linux / macOS
export PY_COV_MIN=65
./scripts/test_prep.sh
```

### Paramètre de script (PowerShell)

```powershell
.\scripts\test_prep.ps1 -CovMin 65
.\scripts\test_ocr.ps1 -CovMin 70
```

### Résolution

```
Priorité:
1. Paramètre -CovMin (si fourni, PowerShell uniquement)
2. Variable d'environnement $PY_COV_MIN / $env:PY_COV_MIN
3. Valeur par défaut: 60
```

## 📈 Zones à améliorer en priorité

### prep-service (+7% nécessaire)

```
┌─────────────────────┬────────┬──────────────────────┐
│ Fichier             │ Actuel │ Action               │
├─────────────────────┼────────┼──────────────────────┤
│ logger.py           │   0%   │ ⚠️ Créer test_logger │
│ utils.py            │  53%   │ 🔧 Compléter tests   │
│ main.py             │  52%   │ 🔧 Tests edges       │
└─────────────────────┴────────┴──────────────────────┘
```

Gain potentiel : **+10%** avec tests logger + utils complets

### orchestrator (+7% nécessaire)

```
┌─────────────────────┬────────┬──────────────────────┐
│ Fichier             │ Actuel │ Action               │
├─────────────────────┼────────┼──────────────────────┤
│ main.py             │  24%   │ ℹ️  Normal (boucle)  │
│ utils.py            │  77%   │ 🔧 Compléter reste   │
│ helpers             │   ?    │ 🔧 Tests helpers     │
└─────────────────────┴────────┴──────────────────────┘
```

Gain potentiel : **+7%** avec utils + helpers

### ocr-service (déjà à 60.25%) ✅

```
┌─────────────────────┬────────┬──────────────────────┐
│ Fichier             │ Actuel │ Action               │
├─────────────────────┼────────┼──────────────────────┤
│ logger.py           │   0%   │ 📝 Bonus: +5%        │
│ main.py             │  ~50%  │ 📝 Bonus: edges      │
└─────────────────────┴────────┴──────────────────────┘
```

Actuellement OK pour seuil 60%, amélioration optionnelle pour 65%

## 🚀 Commandes rapides

### Tester avec seuil par défaut (60%)

```powershell
.\scripts\test_prep.ps1        # Échoue (53.76%)
.\scripts\test_ocr.ps1         # Passe  (60.25%) ✅
.\scripts\test_orchestrator.ps1  # Échoue (53.73%)
```

### Tester avec seuil ajusté temporairement

```powershell
$env:PY_COV_MIN=53
.\scripts\test_prep.ps1        # Passe (53.76% > 53%)
.\scripts\test_orchestrator.ps1  # Passe (53.73% > 53%)
```

⚠️ **Ne PAS utiliser en CI/CD** — objectif = améliorer couverture, pas baisser seuil

### Tester avec seuil cible (70%)

```powershell
.\scripts\test_prep.ps1 -CovMin 70     # Échoue (53.76%)
.\scripts\test_ocr.ps1 -CovMin 70      # Échoue (60.25%)
.\scripts\test_orchestrator.ps1 -CovMin 70  # Échoue (53.73%)
```

Tous échouent actuellement → besoin de tests additionnels

## 📄 Fichiers modifiés

```
scripts/
├── test_prep.ps1          ✅ Modifié (param -CovMin, --cov-fail-under)
├── test_ocr.ps1           ✅ Modifié (param -CovMin, --cov-fail-under)
├── test_orchestrator.ps1  ✅ Modifié (param -CovMin, --cov-fail-under)
├── test_prep.sh           ✅ Modifié (var COV_MIN, --cov-fail-under)
├── test_ocr.sh            ✅ Modifié (var COV_MIN, --cov-fail-under)
└── test_orchestrator.sh   ✅ Modifié (var COV_MIN, --cov-fail-under)

docs/dev/
└── testing.md             ✅ Modifié (section "Seuils de couverture")

docs/ia/rapports-execution/
└── RAPPORT_IMPLEMENTATION_COUVERTURE_2026-03-03.md  ✅ Créé

(racine)/
├── IMPLEMENTATION_COUVERTURE.md  ✅ Créé (ce fichier)
└── IMPLEMENTATION_SUMMARY.md     (existant — tests API)
```

## ✅ Validation

```powershell
# 1. Vérifier affichage du seuil
PS> .\scripts\test_prep.ps1
  > pytest [prep-service] (seuil couverture: 60%)  ✅

# 2. Vérifier paramètre personnalisé
PS> .\scripts\test_ocr.ps1 -CovMin 65
  > pytest [ocr-service] (seuil couverture: 65%)   ✅

# 3. Vérifier variable d'environnement
PS> $env:PY_COV_MIN=70; .\scripts\test_orchestrator.ps1
  > pytest [orchestrator] (seuil couverture: 70%)  ✅
```

## 🎉 Résultat

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   ✅  Tous les livrables du Prompt 4 complétés !    │
│                                                      │
│   • Scripts modifiés (6 fichiers)                   │
│   • Documentation mise à jour                        │
│   • Variable PY_COV_MIN implémentée                 │
│   • Stratégie progressive documentée                 │
│   • Baseline mesurée et validée                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

**Pour plus de détails** :
- Guide utilisateur : `docs/dev/testing.md`
- Rapport technique : `docs/ia/rapports-execution/RAPPORT_IMPLEMENTATION_COUVERTURE_2026-03-03.md`
- Récapitulatif complet : `IMPLEMENTATION_COUVERTURE.md`

