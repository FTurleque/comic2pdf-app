# Notices de licences tierces — Comic2PDF

Ce projet (`comic2pdf-app`) est distribué sous **licence MIT** (voir [`LICENSE`](LICENSE)).

Cependant, il intègre et dépend de composants tiers ayant leurs **propres licences**,
certaines pouvant imposer des **obligations supplémentaires** lors de la distribution.

---

## ⚠️ AVERTISSEMENT IMPORTANT — À lire avant toute distribution

### Ghostscript (AGPL-3.0) — Point critique

> **Ghostscript est distribué sous licence AGPL-3.0 (GNU Affero General Public License v3.0).**
>
> L'utilisation de Ghostscript dans un produit distribué **peut déclencher l'obligation de publier
> le code source complet de l'application dérivée**, y compris si le logiciel est fourni comme
> service en réseau (SaaS), selon les conditions de l'AGPL-3.0.
>
> **⚠️ Vérifiez impérativement la conformité de votre distribution avant tout usage commercial
> ou redistribution d'un binaire intégrant Ghostscript.**
>
> Lien officiel : <https://www.ghostscript.com/licensing/index.html>

### 7-Zip / p7zip-full — Licence hybride (point d'attention)

> **Le package `p7zip-full` (Debian/Ubuntu) peut extraire les archives RAR (format `.cbr`).**
>
> La base 7-Zip est principalement sous licence **LGPL** (parties), mais le support du format RAR
> est soumis à une **licence UNRAR propriétaire distincte**, qui interdit notamment la création
> d'outils de compression RAR et peut restreindre certains usages de la décompression.
>
> **⚠️ À confirmer selon la chaîne d'extraction réellement utilisée (CBR = RAR) et les binaires
> embarqués dans le conteneur Docker.**
>
> Lien officiel : <https://www.7-zip.org/license.txt>

---

## Composants tiers

### Services Python (Docker)

| Composant | Usage dans le projet | Licence | Lien officiel |
|---|---|---|---|
| **7-Zip / p7zip-full** | Extraction des archives `.cbz` (ZIP) et `.cbr` (RAR) dans `prep-service` | LGPL (base) + UNRAR propriétaire (RAR) — **À confirmer** | <https://www.7-zip.org/license.txt> |
| **img2pdf** | Conversion des images extraites en `raw.pdf` dans `prep-service` | LGPL-2.1 ou ultérieure | <https://gitlab.mister-muffin.de/josch/img2pdf> |
| **FastAPI** | Framework HTTP REST pour `prep-service` et `ocr-service` | MIT | <https://github.com/tiangolo/fastapi/blob/master/LICENSE> |
| **Uvicorn** | Serveur ASGI pour `prep-service` et `ocr-service` | BSD-3-Clause | <https://github.com/encode/uvicorn/blob/master/LICENSE.md> |
| **Pydantic** | Validation des modèles de requête FastAPI | MIT | <https://github.com/pydantic/pydantic/blob/main/LICENSE> |
| **OCRmyPDF** | Moteur principal d'OCR : `raw.pdf` → `final.pdf` dans `ocr-service` | MPL-2.0 (Mozilla Public License 2.0) | <https://github.com/ocrmypdf/OCRmyPDF/blob/main/LICENSE> |
| **Tesseract OCR** | Moteur de reconnaissance optique de caractères (appelé par OCRmyPDF) | Apache-2.0 | <https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE> |
| **Ghostscript** | Rendu et optimisation PDF (requis par OCRmyPDF) | **AGPL-3.0** ⚠️ — voir avertissement ci-dessus | <https://www.ghostscript.com/licensing/index.html> |
| **qpdf** | Manipulation PDF (requis par OCRmyPDF) | Apache-2.0 — **À confirmer** | <https://github.com/qpdf/qpdf/blob/main/LICENSE.txt> |
| **unpaper** | Nettoyage des images avant OCR (requis par OCRmyPDF) | GPL-2.0 — **À confirmer** | <https://github.com/unpaper/unpaper/blob/main/COPYING> |
| **Requests** | Client HTTP Python dans `orchestrator` | Apache-2.0 | <https://github.com/psf/requests/blob/main/LICENSE> |

### Application Desktop (JavaFX)

| Composant | Usage dans le projet | Licence | Lien officiel |
|---|---|---|---|
| **OpenJFX / JavaFX 21** | Framework UI de l'application desktop (`desktop-app`) | GPL-2.0 with Classpath Exception | <https://openjdk.org/legal/gplv2+ce.html> |
| **Jackson Databind** | Sérialisation/désérialisation JSON dans `desktop-app` | Apache-2.0 | <https://github.com/FasterXML/jackson-databind/blob/2.x/LICENSE> |
| **JUnit 5 (Jupiter)** | Framework de tests unitaires Java | EPL-2.0 | <https://github.com/junit-team/junit5/blob/main/LICENSE.md> |
| **TestFX** | Tests UI JavaFX (scope `test` uniquement) | EUPL-1.1 — **À confirmer** | <https://github.com/TestFX/TestFX/blob/master/LICENSE.md> |
| **OpenJFX Monocle** | Rendu headless pour tests UI (scope `test` uniquement) | GPL-2.0 with Classpath Exception — **À confirmer** | <https://github.com/TestFX/Monocle> |

### Dépendances de développement/test Python

| Composant | Usage dans le projet | Licence | Lien officiel |
|---|---|---|---|
| **pytest** | Framework de tests Python | MIT | <https://github.com/pytest-dev/pytest/blob/main/LICENSE> |
| **pytest-mock** | Fixtures de mock pour pytest | MIT | <https://github.com/pytest-dev/pytest-mock/blob/main/LICENSE> |
| **pytest-cov** | Couverture de code pour pytest | MIT | <https://github.com/pytest-dev/pytest-cov/blob/master/LICENSE> |
| **httpx** | Client HTTP async (tests FastAPI) | BSD-3-Clause | <https://github.com/encode/httpx/blob/master/LICENSE.md> |
| **Pillow** | Génération d'images de test (smoke tests `prep-service`) | HPND (Historical Permission Notice and Disclaimer) | <https://github.com/python-pillow/Pillow/blob/main/LICENSE> |

---

## Notes de distribution

> **Le projet `comic2pdf-app` est sous licence MIT.**
> Cette licence s'applique au **code source de ce dépôt uniquement**.

Lors de la **distribution d'un binaire ou d'une image Docker** basée sur ce projet,
les licences des dépendances tierces s'appliquent indépendamment et peuvent imposer
des obligations supplémentaires :

1. **⚠️ Ghostscript (AGPL-3.0) — Point critique absolu**
   La redistribution d'un produit intégrant Ghostscript peut imposer la publication
   du code source complet de l'ensemble de l'application dérivée.
   **Consultez un conseiller juridique avant toute distribution commerciale.**

2. **⚠️ 7-Zip / RAR — À confirmer**
   L'extraction de fichiers `.cbr` (format RAR) via `p7zip-full` peut être soumise
   à la licence UNRAR propriétaire. À vérifier selon les binaires réellement inclus
   dans l'image Docker et la version de `p7zip-full` installée.

3. **unpaper (GPL-2.0 — À confirmer)**
   Si la licence est effectivement GPL-2.0 (non LGPL), cela peut imposer des
   obligations copyleft sur les composants liés lors de la distribution.

4. **OpenJFX (GPL-2.0 + Classpath Exception)**
   L'exception Classpath permet l'utilisation d'OpenJFX dans des applications
   propriétaires sans déclencher le copyleft GPL, à condition de ne pas modifier
   OpenJFX lui-même.

---

*Ce fichier est fourni à titre informatif. Il ne constitue pas un avis juridique.
En cas de doute sur la conformité de votre distribution, consultez un conseiller juridique
spécialisé en droit des licences logicielles.*

*Pour toute question, ouvrir une issue dans le dépôt et taguer `@team-architecture`.*

