"""
Conftest pour les tests tools/ — ajoute la racine du repo dans sys.path
afin que `import tools.*` fonctionne quel que soit le répertoire de lancement.
"""
import os
import sys

# __file__ est N:/workspace-dev/comic2pdf-app/tests/tools/conftest.py
# On remonte de 2 niveaux pour atteindre la racine du repo
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
