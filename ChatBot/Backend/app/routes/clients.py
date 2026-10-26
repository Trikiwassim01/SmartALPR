from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Client, status_code=201)
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    """
    Créer un nouveau client
    """
    # Vérifier si le numéro existe déjà
    existing_client = db.query(models.Client).filter(models.Client.num == client.num).first()
    if existing_client:
        raise HTTPException(status_code=400, detail="Ce numéro de client existe déjà")
    
    db_client = models.Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/", response_model=List[schemas.Client])
def read_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Récupérer tous les clients avec pagination
    """
    clients = db.query(models.Client).offset(skip).limit(limit).all()
    return clients

@router.get("/{client_id}", response_model=schemas.Client)
def read_client(client_id: int, db: Session = Depends(get_db)):
    """
    Récupérer un client par son ID
    """
    db_client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    return db_client

@router.put("/{client_id}", response_model=schemas.Client)
def update_client(
    client_id: int,
    client_update: schemas.ClientCreate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour un client
    """
    db_client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Vérifier si le nouveau numéro existe déjà
    if client_update.num != db_client.num:
        existing = db.query(models.Client).filter(
            models.Client.num == client_update.num,
            models.Client.id != client_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Numéro déjà utilisé")
    
    # Mettre à jour
    for field, value in client_update.dict().items():
        setattr(db_client, field, value)
    
    db.commit()
    db.refresh(db_client)
    return db_client

@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un client
    """
    db_client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Vérifier s'il a des voitures
    if db_client.voitures:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un client avec des voitures"
        )
    
    db.delete(db_client)
    db.commit()
    return None

@router.get("/{client_id}/voitures", response_model=List[schemas.Voiture])
def get_client_voitures(client_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les voitures d'un client
    """
    db_client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return db_client.voitures

@router.get("/search/", response_model=List[schemas.Client])
def search_clients(
    nom: Optional[str] = None,
    prenom: Optional[str] = None,
    num: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Rechercher des clients
    """
    query = db.query(models.Client)
    
    if nom:
        query = query.filter(models.Client.nom.ilike(f"%{nom}%"))
    if prenom:
        query = query.filter(models.Client.prenom.ilike(f"%{prenom}%"))
    if num:
        query = query.filter(models.Client.num.ilike(f"%{num}%"))
    
    return query.all()