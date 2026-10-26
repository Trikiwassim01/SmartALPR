from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from .. import schemas, models
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Historique, status_code=201)
def create_historique(historique: schemas.HistoriqueCreate, db: Session = Depends(get_db)):
    """
    Créer un nouvel historique de réparation
    """
    # Vérifier si la voiture existe
    voiture = db.query(models.Voiture).filter(
        models.Voiture.matricule == historique.voiture_matricule
    ).first()
    if not voiture:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")
    
    # Créer l'historique
    historique_data = historique.dict()
    piece_ids = historique_data.pop("piece_ids", [])
    tarif_ids = historique_data.pop("tarif_ids", [])
    
    db_historique = models.Historique(**historique_data)
    
    # Ajouter les pièces
    for piece_id in piece_ids:
        piece = db.query(models.Piece).filter(models.Piece.id == piece_id).first()
        if piece:
            db_historique.pieces.append(piece)
    
    # Ajouter les tarifs
    for tarif_id in tarif_ids:
        tarif = db.query(models.TarifReparation).filter(
            models.TarifReparation.id == tarif_id
        ).first()
        if tarif:
            db_historique.tarifs_reparation.append(tarif)
    
    db.add(db_historique)
    db.commit()
    db.refresh(db_historique)
    return db_historique

@router.get("/", response_model=List[schemas.Historique])
def read_historiques(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    voiture_matricule: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer tous les historiques
    """
    query = db.query(models.Historique)
    
    if date_debut:
        query = query.filter(models.Historique.date >= date_debut)
    if date_fin:
        query = query.filter(models.Historique.date <= date_fin)
    if voiture_matricule:
        query = query.filter(models.Historique.voiture_matricule == voiture_matricule)
    
    historiques = query.offset(skip).limit(limit).all()
    return historiques

@router.get("/{historique_id}", response_model=schemas.Historique)
def read_historique(historique_id: int, db: Session = Depends(get_db)):
    """
    Récupérer un historique par son ID
    """
    historique = db.query(models.Historique).filter(models.Historique.id == historique_id).first()
    if historique is None:
        raise HTTPException(status_code=404, detail="Historique non trouvé")
    return historique

@router.get("/{historique_id}/pieces", response_model=List[schemas.Piece])
def get_historique_pieces(historique_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les pièces d'un historique
    """
    historique = db.query(models.Historique).filter(models.Historique.id == historique_id).first()
    if historique is None:
        raise HTTPException(status_code=404, detail="Historique non trouvé")
    
    return historique.pieces

@router.get("/{historique_id}/tarifs", response_model=List[schemas.TarifReparation])
def get_historique_tarifs(historique_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les tarifs d'un historique
    """
    historique = db.query(models.Historique).filter(models.Historique.id == historique_id).first()
    if historique is None:
        raise HTTPException(status_code=404, detail="Historique non trouvé")
    
    return historique.tarifs_reparation

@router.delete("/{historique_id}", status_code=204)
def delete_historique(historique_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un historique
    """
    historique = db.query(models.Historique).filter(models.Historique.id == historique_id).first()
    if historique is None:
        raise HTTPException(status_code=404, detail="Historique non trouvé")
    
    db.delete(historique)
    db.commit()
    return None

@router.get("/statistiques/montant-total")
def get_montant_total(
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Obtenir le montant total des réparations
    """
    query = db.query(models.Historique)
    
    if date_debut:
        query = query.filter(models.Historique.date >= date_debut)
    if date_fin:
        query = query.filter(models.Historique.date <= date_fin)
    
    historiques = query.all()
    total = sum(h.montant_reparation + h.montant_pieces for h in historiques)
    
    return {"montant_total": total, "nombre_reparations": len(historiques)}