# Licences Python — dépendances runtime directes

> **Généré par** : snapshot manuel initial — 2026-03-06.
> Mis à jour via l'artefact CI `python-licenses-<service>` du job `licenses-snapshot`
> dans [`.github/workflows/dependency-audit.yml`](../../.github/workflows/dependency-audit.yml)
> (rétention 30 jours).

---

## ⚠️ Périmètre et limitations

| Point | Détail |
|---|---|
| **Dépendances couvertes** | Runtime directes uniquement (`requirements.txt` de chaque service) |
| **Dépendances exclues** | Dev/test (`requirements-dev.txt`) — couvertes par les audits de sécurité |
| **Binaires système exclus** | Ghostscript, Tesseract, 7-Zip, qpdf, unpaper → voir [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) |
| **Versions** | `unpinned` jusqu'à la PR `chore/pin-dependencies` (pip-tools). L'artefact CI reflète les versions installées au run (meilleur cas, non reproductible). Après pinning : versions fixes reproductibles. |
| **Transitives** | Non listées ici. L'artefact CI `python-licenses-<service>` couvre directes + transitives (résultat de `pip install -r requirements.txt`). |

---

## prep-service (`services/prep-service/requirements.txt`)

| Package | Version (CI) | Licence | URL |
|---|---|---|---|
| fastapi | unpinned | MIT | https://github.com/tiangolo/fastapi |
| uvicorn | unpinned | BSD-3-Clause | https://github.com/encode/uvicorn |
| img2pdf | unpinned | LGPL-2.1+ | https://gitlab.mister-muffin.de/josch/img2pdf |

---

## ocr-service (`services/ocr-service/requirements.txt`)

| Package | Version (CI) | Licence | URL |
|---|---|---|---|
| fastapi | unpinned | MIT | https://github.com/tiangolo/fastapi |
| uvicorn | unpinned | BSD-3-Clause | https://github.com/encode/uvicorn |
| ocrmypdf | unpinned | MPL-2.0 | https://github.com/ocrmypdf/OCRmyPDF |

> **Note** : `ocrmypdf` installe un grand nombre de dépendances transitives
> (`pikepdf`, `Pillow`, `pdfminer.six`, `reportlab`, etc.).
> Ces transitives apparaissent dans l'artefact CI `python-licenses-ocr-service`
> (job `licenses-snapshot`, workflow `dependency-audit.yml`).

---

## orchestrator (`services/orchestrator/requirements.txt`)

| Package | Version (CI) | Licence | URL |
|---|---|---|---|
| requests | unpinned | Apache-2.0 | https://github.com/psf/requests |

---

## tools (`tools/requirements.txt`)

| Package | Version (CI) | Licence | URL |
|---|---|---|---|
| img2pdf | unpinned | LGPL-2.1+ | https://gitlab.mister-muffin.de/josch/img2pdf |

---

## Prochaine étape

Après la PR **`chore/pin-dependencies`** (pip-tools) :
- Remplacer les `unpinned` par les versions épinglées issues de `pip-compile`.
- L'artefact CI deviendra reproductible (arbre transitif résolu à versions fixes).
- Ce snapshot sera mis à jour à chaque cycle Dependabot.

---

*Ce fichier ne constitue pas un avis juridique.
Pour des questions de conformité, consulter un spécialiste en droit des licences logicielles.*

