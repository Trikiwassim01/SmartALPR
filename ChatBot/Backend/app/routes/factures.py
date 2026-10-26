from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from .. import schemas, models
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Facture, status_code=201)
def create_facture(facture: schemas.FactureCreate, db: Session = Depends(get_db)):
    """
    Créer une nouvelle facture
    """
    # Vérifier si le numéro de facture existe déjà
    existing = db.query(models.Facture).filter(
        models.Facture.numero_facture == facture.numero_facture
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Numéro de facture déjà utilisé")
    
    # Vérifier si le client existe
    client = db.query(models.Client).filter(models.Client.id == facture.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Vérifier si l'historique existe
    historique = db.query(models.Historique).filter(
        models.Historique.id == facture.historique_id
    ).first()
    if not historique:
        raise HTTPException(status_code=404, detail="Historique non trouvé")
    
    db_facture = models.Facture(**facture.dict())
    db.add(db_facture)
    db.commit()
    db.refresh(db_facture)
    return db_facture

@router.get("/", response_model=List[schemas.Facture])
def read_factures(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer toutes les factures
    """
    query = db.query(models.Facture)
    
    if date_debut:
        query = query.filter(models.Facture.date_facture >= date_debut)
    if date_fin:
        query = query.filter(models.Facture.date_facture <= date_fin)
    if client_id:
        query = query.filter(models.Facture.client_id == client_id)
    
    factures = query.offset(skip).limit(limit).all()
    return factures

@router.get("/{numero_facture}", response_model=schemas.Facture)
def read_facture(numero_facture: str, db: Session = Depends(get_db)):
    """
    Récupérer une facture par son numéro
    """
    facture = db.query(models.Facture).filter(
        models.Facture.numero_facture == numero_facture
    ).first()
    if facture is None:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    return facture

@router.get("/client/{client_id}", response_model=List[schemas.Facture])
def get_client_factures(client_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les factures d'un client
    """
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return client.factures

@router.get("/{numero_facture}/details")
def get_facture_details(numero_facture: str, db: Session = Depends(get_db)):
    """
    Obtenir les détails complets d'une facture
    """
    facture = db.query(models.Facture).filter(
        models.Facture.numero_facture == numero_facture
    ).first()
    
    if facture is None:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    return {
        "facture": facture,
        "client": facture.client,
        "historique": facture.historique,
        "voiture": facture.historique.voiture if facture.historique else None
    }

@router.delete("/{numero_facture}", status_code=204)
def delete_facture(numero_facture: str, db: Session = Depends(get_db)):
    """
    Supprimer une facture
    """
    facture = db.query(models.Facture).filter(
        models.Facture.numero_facture == numero_facture
    ).first()
    if facture is None:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    db.delete(facture)
    db.commit()
    return None