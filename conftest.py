"""
Conftest racine du repo comic2pdf-app.

Injecte le répertoire racine dans sys.path pour permettre les imports
absolus de type ``import tools.*`` depuis n'importe quel sous-dossier de tests.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

