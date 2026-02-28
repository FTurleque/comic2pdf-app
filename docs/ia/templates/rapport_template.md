# RAPPORT_<TYPE>_YYYY-MM-DD

> **Généré par IA** — Outil/Agent : `[GitHub Copilot / nom-agent]`
> **Auteur responsable** : `[Prénom NOM — identifiant GitHub]`

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Titre** | `[Titre court du rapport]` |
| **Type** | `IMPLEMENTATION` / `ANALYSE` / `MIGRATION` / `SECURITE` |
| **Date** | `YYYY-MM-DD` |
| **Auteur(s)** | `[Prénom NOM]` |
| **Équipe** | `comic2pdf-app` |
| **PR / Issue associée** | `#[numéro]` — `[lien]` |

---

## 2. Contexte et résumé

> *2 à 4 phrases décrivant le contexte de la demande et l'objectif du rapport.*

[Décrire ici le contexte : pourquoi cette tâche a été demandée, quel problème elle résout,
quelle partie du système est concernée (prep-service / ocr-service / orchestrator / desktop-app).]

---

## 3. Description des changements

> *Liste synthétique des modifications apportées.*

### Fichiers modifiés

| Fichier | Type | Description de la modification |
|---|---|---|
| `services/orchestrator/app/utils.py` | Modifié | [description] |
| `services/orchestrator/app/core.py` | Modifié | [description] |
| `[chemin/fichier]` | Nouveau / Modifié / Supprimé | [description] |

### Variables d'environnement ajoutées

| Variable | Service | Défaut | Description |
|---|---|---|---|
| `[NOM_VAR]` | [service] | `[valeur]` | [description] |

### Endpoints HTTP ajoutés / modifiés

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/metrics` | [description] |
| `POST` | `/config` | [description] |

---

## 4. Étapes pour reproduire / commandes exécutées

```powershell
# Installer les dépendances et lancer les tests Python
cd services\orchestrator
python -m pip install -r requirements-dev.txt
python -m pytest -q

# Lancer les tests Java
cd desktop-app
mvn -q test

# Script global
.\run_tests.ps1
```

### Résultats des tests

| Module | Tests | Résultat |
|---|---|---|
| `prep-service` | [N] | ✅ PASS |
| `ocr-service` | [N] | ✅ PASS |
| `orchestrator` | [N] | ✅ PASS |
| `desktop-app` | [N] | ✅ PASS |

---

## 5. Points d'attention / Limitations

> *Ce qui n'a pas été implémenté, ce qui est reporté, les risques identifiés.*

- [Point d'attention 1]
- [Point d'attention 2]

---

## 6. Liens et références

- PR : `[lien vers la PR]`
- Issue : `[lien vers l'issue]`
- Politique rapports IA : `.github/instructions/reports-docs.instructions.md`
- Instructions Copilot : `.github/copilot-instructions.md`

---

## 7. Contact

Pour des questions sur ce rapport, ouvrir une issue dans le dépôt et taguer `@team-architecture`.

