from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Piece, status_code=201)
def create_piece(piece: schemas.PieceCreate, db: Session = Depends(get_db)):
    """
    Ajouter une nouvelle pièce
    """
    # Vérifier si la pièce existe déjà (même nom)
    existing = db.query(models.Piece).filter(
        models.Piece.nom_piece == piece.nom_piece
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cette pièce existe déjà")
    
    db_piece = models.Piece(**piece.dict())
    db.add(db_piece)
    db.commit()
    db.refresh(db_piece)
    return db_piece

@router.get("/", response_model=List[schemas.Piece])
def read_pieces(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    nom: Optional[str] = None,
    min_prix: Optional[float] = None,
    max_prix: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer toutes les pièces
    """
    query = db.query(models.Piece)
    
    if nom:
        query = query.filter(models.Piece.nom_piece.ilike(f"%{nom}%"))
    if min_prix:
        query = query.filter(models.Piece.prix_unitaire >= min_prix)
    if max_prix:
        query = query.filter(models.Piece.prix_unitaire <= max_prix)
    
    pieces = query.offset(skip).limit(limit).all()
    return pieces

@router.get("/{piece_id}", response_model=schemas.Piece)
def read_piece(piece_id: int, db: Session = Depends(get_db)):
    """
    Récupérer une pièce par son ID
    """
    piece = db.query(models.Piece).filter(models.Piece.id == piece_id).first()
    if piece is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")
    return piece

@router.put("/{piece_id}", response_model=schemas.Piece)
def update_piece(
    piece_id: int,
    piece_update: schemas.PieceCreate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour une pièce
    """
    piece = db.query(models.Piece).filter(models.Piece.id == piece_id).first()
    if piece is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")
    
    # Mettre à jour
    for field, value in piece_update.dict().items():
        setattr(piece, field, value)
    
    db.commit()
    db.refresh(piece)
    return piece

@router.delete("/{piece_id}", status_code=204)
def delete_piece(piece_id: int, db: Session = Depends(get_db)):
    """
    Supprimer une pièce
    """
    piece = db.query(models.Piece).filter(models.Piece.id == piece_id).first()
    if piece is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")
    
    db.delete(piece)
    db.commit()
    return None

@router.get("/{piece_id}/historiques", response_model=List[schemas.Historique])
def get_piece_historiques(piece_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les historiques utilisant cette pièce
    """
    piece = db.query(models.Piece).filter(models.Piece.id == piece_id).first()
    if piece is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")
    
    return piece.historiques

@router.get("/statistiques/utilisation")
def get_statistiques_pieces(db: Session = Depends(get_db)):
    """
    Obtenir les statistiques d'utilisation des pièces
    """
    pieces = db.query(models.Piece).all()
    
    result = []
    for piece in pieces:
        total_utilise = sum(h.quantite for h in piece.historiques)
        result.append({
            "piece": piece.nom_piece,
            "quantite_totale": total_utilise,
            "valeur_totale": total_utilise * piece.prix_unitaire
        })
    
    return result