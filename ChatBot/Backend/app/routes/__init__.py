# app/routes/__init__.py
"""
Package contenant toutes les routes de l'API
"""

# Import des routeurs pour les exposer
from .clients import router as clients_router
from .voitures import router as voitures_router
from .historiques import router as historiques_router
from .factures import router as factures_router
from .pieces import router as pieces_router
from .tarifs import router as tarifs_router

# Liste de tous les routeurs disponibles
__all__ = [
    "clients_router",
    "voitures_router",
    "historiques_router",
    "factures_router",
    "pieces_router",
    "tarifs_router",
]

# Optionnel : créer un routeur principal si nécessaire
# from fastapi import APIRouter
# main_router = APIRouter()
# main_router.include_router(clients_router, prefix="/clients", tags=["Clients"])
# ... etc.