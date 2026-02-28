# Feature: Mode CLI standalone et watch-folder local sans Docker

## Goal
Fournir un mode d’utilisation sans interface graphique et sans dépendance à Docker, afin que les utilisateurs avancés puissent convertir des fichiers en ligne de commande ou exécuter l’orchestrateur en local.

## Contexte
Le flux actuel repose sur Docker pour lancer les services et l’orchestrateur. Certains utilisateurs souhaiteraient convertir un seul fichier (`comic2pdf`) ou exécuter un watch‑folder sur leur système local, en utilisant uniquement Python et Java.

## Tâches
1. Implémentez un script CLI Python `comic2pdf` (par exemple dans `tools/cli.py`) qui :
   - Accepte un chemin vers un fichier `.cbz`/`.cbr` et des options (`--lang`, `--dpi`, `--fast-mode`, etc.).
   - Lance `prep-service` puis `ocr-service` en local (via import direct ou via HTTP si services tournent déjà).
   - Affiche le chemin du fichier PDF final et le temps de conversion.
   - Gère les erreurs (taille, signature, disk_error).
2. Implémentez un mode « watch-folder local » :
   - Fournissez un script (par exemple `tools/watch_local.py`) qui réutilise la logique de l’orchestrateur pour surveiller un dossier spécifié, traiter les fichiers en séquence ou en parallèle, et écrire les sorties dans un dossier cible.
   - Ce script devra réutiliser `prep-service` et `ocr-service` en local. Pensez à factoriser le code commun avec l’orchestrateur (découverte de fichiers, déduplication, etc.).
   - Ajoutez des options de ligne de commande pour configurer la concurrence et les paramètres OCR.
3. Ajoutez un test d’intégration minimal qui :
   - Crée un petit fichier `.cbz` de test.
   - Lance le script `comic2pdf` et vérifie que le PDF est généré dans le dossier `out`.
   - Utilise des mocks pour les appels `subprocess` afin de ne pas exécuter `7z` et `ocrmypdf` pour de vrai.
4. Ajoutez une section à la documentation expliquant comment utiliser ces scripts (installation Python, activation de l’environnement virtuel, lancement).

## Contraintes
- Le mode CLI ne doit pas nécessiter Docker, mais il peut détecter des services existants et les utiliser si disponibles.
- Réutilisez autant que possible le code existant pour éviter la duplication.
