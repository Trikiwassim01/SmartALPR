# app/__init__.py
"""
Package principal de l'application Garage Management API
"""

# Import des modules principaux pour faciliter l'accès
from .main import app
from .database import engine, SessionLocal, Base, get_db
from . import models, schemas, crud

__version__ = "1.0.0"
__author__ = "Garage Management Team"

# Liste des modules exportés
__all__ = [
    "app",
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "models",
    "schemas",
    "crud",
]