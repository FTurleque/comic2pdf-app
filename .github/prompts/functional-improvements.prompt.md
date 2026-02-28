# Feature: Améliorations fonctionnelles – reprise intelligente, options OCR avancées, support WebP

## Goal
Ajouter des fonctions qui optimisent le flux de travail : passer les étapes PREP ou OCR lorsqu’un artefact valide est déjà présent, offrir des options de configuration avancées pour l’OCR et assurer le support des formats d’image modernes comme WebP.

## Contexte
Le système recalcul complet à chaque tentative (politique B)【116166737120233†L24-L47】. Les options OCR actuelles sont limitées (langue, deskew, rotate, optimize) et le support WebP n’est pas garanti par `img2pdf`.

## Tâches
1. Ajoutez une variable `ENABLE_SMART_RESUME` (`true/false`). Lorsque activée :
   - Avant de lancer PREP, si `raw.pdf` existe déjà et est validé par `validate_pdf()`, sautez directement à l’étape OCR.
   - Avant de lancer OCR, si `final.pdf` existe et est valide, sautez l’étape OCR et marquez le job `DONE`.
   - Journalisez le fait que l’étape a été sautée et mettez à jour les métriques (`prep_skipped`, `ocr_skipped`).
2. Étendre l’interface OCR pour accepter des options avancées via un paramètre `options` dans la requête POST :
   - `dpi` (entier, ex : 300)
   - `fast_mode` (booléen) pour utiliser les options rapides d’OCRmyPDF (comme `--fast-webp`).
   - `remove_background` (booléen) pour appeler `ocrmypdf --remove-background`.
   - `sidecar_txt` (booléen) pour générer un fichier `.txt` contenant le texte OCR.
   Mettez à jour `ocr-service` pour transmettre ces options à `ocrmypdf` et inclure ces valeurs dans le calcul de `profileHash`.
3. Ajoutez le support des images WebP dans `prep-service` :
   - Essayez d’utiliser directement `img2pdf` ; s’il échoue, convertissez les images WebP en PNG avec `Pillow` (lib dev‑only) avant l’assemblage.
   - Ajoutez un test qui crée une image WebP dans un tmpdir et vérifie que la conversion en PDF fonctionne.
4. Mettez à jour le profil OCR pour normaliser les options avancées et ordonner les langues afin que `profileHash` soit déterministe.
5. Ajoutez des tests pour :
   - Vérifier que `ENABLE_SMART_RESUME=true` saute correctement l’étape PREP.
   - Vérifier que `options.dpi=150` est bien transmis à `ocrmypdf`.
   - Vérifier la génération d’un `.txt` sidecar lorsque `sidecar_txt=true`.
   - Vérifier la conversion d’une image WebP en PDF.

## Contraintes
- Les nouvelles options doivent rester facultatives et rétro‑compatibles (comportement inchangé si non utilisées).
- Incluez les versions des outils et les options avancées dans le calcul du `profileHash` pour que la déduplication fonctionne correctement【116166737120233†L24-L47】.
