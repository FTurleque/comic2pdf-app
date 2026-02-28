# Feature: Packaging et ergonomie du produit

## Goal
Préparer `comic2pdf-app` à être distribué comme produit fini avec une interface conviviale, en créant des exécutables pour Windows et macOS, en améliorant l’ergonomie de l’interface et en fournissant une documentation utilisateur complète.

## Contexte
Le projet est actuellement destiné à un usage interne avec Docker. Pour être distribué à des utilisateurs finaux, l’application doit être empaquetée, installer Docker ou proposer un mode sans Docker, fournir des icônes et une expérience cohérente et documentée.

## Tâches
1. Préparer un packaging Windows et macOS :
   - Pour l’application Desktop, utilisez `jpackage` (JDK 16+) ou un outil équivalent pour créer un installeur `.exe` (Windows) et `.dmg` (macOS) avec toutes les dépendances.
   - Inclure l’icône de l’application et un raccourci.
   - Fournir un script post‑installation qui vérifie la présence de Docker et, si absent, propose d’installer Docker Desktop ou d’activer le mode local sans Docker.
2. Préparer un packaging pour la partie services :
   - Créez un script d’installation Python (`pip install .`) ou un exécutable `--onefile` via PyInstaller pour les services et l’orchestrateur.
   - Documentez comment lancer les services en local, comment configurer `services/orchestrator` et comment mettre à jour la configuration.
3. Améliorer l’ergonomie de l’interface :
   - Ajoutez une icône et des couleurs harmonisées dans la JavaFX.
   - Ajoutez des messages d’erreur explicites et des bulles d’aide (tooltip) pour chaque champ.
   - Ajoutez un guide pas à pas (welcome tour) pour les nouveaux utilisateurs.
   - Ajoutez une boîte de dialogue « À propos » avec la version de l’application et les licences tierces.
4. Rédiger la documentation utilisateur :
   - Décrivez l’installation (Windows/macOS/Linux).
   - Expliquez les modes Docker et local.
   - Décrivez les formats supportés (.cbz, .cbr), les options OCR, la gestion des doublons et les limites de taille.
   - Ajoutez une FAQ et une section de dépannage (comment diagnostiquer une erreur, comment augmenter le timeout, etc.).
5. Ajoutez des tests automatisés pour vérifier que :
   - Les scripts d’installation génèrent les exécutables sans erreur.
   - Les exécutables se lancent et affichent la fenêtre principale.
   - Les icônes sont présentes dans le paquet final.

## Contraintes
- Respectez les licences des outils tiers (7-Zip, OCRmyPDF, Tesseract) et documentez-les.
- Ne publiez pas encore l’installateur ; préparez simplement le script et le pipeline.
