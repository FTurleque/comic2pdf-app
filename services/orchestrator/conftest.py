"""
conftest.py — Orchestrateur
Ajoute la racine du service dans sys.path afin que les imports `app.*`
fonctionnent dans les tests pytest sans préfixe de package.
Reconnu automatiquement par pytest et par l'analyseur statique JetBrains.
"""
import sys
import os

# Insère la racine du service (contenant le package `app/`) en tête de path.
sys.path.insert(0, os.path.dirname(__file__))

