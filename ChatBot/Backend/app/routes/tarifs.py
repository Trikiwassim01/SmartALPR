from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.TarifReparation, status_code=201)
def create_tarif(tarif: schemas.TarifReparationCreate, db: Session = Depends(get_db)):
    """
    Créer un nouveau tarif de réparation
    """
    # Vérifier si le type existe déjà
    existing = db.query(models.TarifReparation).filter(
        models.TarifReparation.type_reparation == tarif.type_reparation
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce type de réparation existe déjà")
    
    db_tarif = models.TarifReparation(**tarif.dict())
    db.add(db_tarif)
    db.commit()
    db.refresh(db_tarif)
    return db_tarif

@router.get("/", response_model=List[schemas.TarifReparation])
def read_tarifs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type_reparation: Optional[str] = None,
    min_prix: Optional[float] = None,
    max_prix: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer tous les tarifs
    """
    query = db.query(models.TarifReparation)
    
    if type_reparation:
        query = query.filter(models.TarifReparation.type_reparation.ilike(f"%{type_reparation}%"))
    if min_prix:
        query = query.filter(models.TarifReparation.prix >= min_prix)
    if max_prix:
        query = query.filter(models.TarifReparation.prix <= max_prix)
    
    tarifs = query.offset(skip).limit(limit).all()
    return tarifs

@router.get("/{tarif_id}", response_model=schemas.TarifReparation)
def read_tarif(tarif_id: int, db: Session = Depends(get_db)):
    """
    Récupérer un tarif par son ID
    """
    tarif = db.query(models.TarifReparation).filter(models.TarifReparation.id == tarif_id).first()
    if tarif is None:
        raise HTTPException(status_code=404, detail="Tarif non trouvé")
    return tarif

@router.put("/{tarif_id}", response_model=schemas.TarifReparation)
def update_tarif(
    tarif_id: int,
    tarif_update: schemas.TarifReparationCreate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour un tarif
    """
    tarif = db.query(models.TarifReparation).filter(models.TarifReparation.id == tarif_id).first()
    if tarif is None:
        raise HTTPException(status_code=404, detail="Tarif non trouvé")
    
    # Vérifier si le nouveau type existe déjà
    if tarif_update.type_reparation != tarif.type_reparation:
        existing = db.query(models.TarifReparation).filter(
            models.TarifReparation.type_reparation == tarif_update.type_reparation
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ce type existe déjà")
    
    # Mettre à jour
    for field, value in tarif_update.dict().items():
        setattr(tarif, field, value)
    
    db.commit()
    db.refresh(tarif)
    return tarif

@router.delete("/{tarif_id}", status_code=204)
def delete_tarif(tarif_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un tarif
    """
    tarif = db.query(models.TarifReparation).filter(models.TarifReparation.id == tarif_id).first()
    if tarif is None:
        raise HTTPException(status_code=404, detail="Tarif non trouvé")
    
    db.delete(tarif)
    db.commit()
    return None

@router.get("/{tarif_id}/historiques", response_model=List[schemas.Historique])
def get_tarif_historiques(tarif_id: int, db: Session = Depends(get_db)):
    """
    Récupérer les historiques utilisant ce tarif
    """
    tarif = db.query(models.TarifReparation).filter(models.TarifReparation.id == tarif_id).first()
    if tarif is None:
        raise HTTPException(status_code=404, detail="Tarif non trouvé")
    
    return tarif.historiques

@router.get("/statistiques/popularite")
def get_popularite_tarifs(db: Session = Depends(get_db)):
    """
    Obtenir la popularité des différents types de réparation
    """
    tarifs = db.query(models.TarifReparation).all()
    
    result = []
    for tarif in tarifs:
        nombre_utilisations = len(tarif.historiques)
        result.append({
            "type_reparation": tarif.type_reparation,
            "prix": tarif.prix,
            "nombre_utilisations": nombre_utilisations,
            "periode_moyenne": tarif.periode_reparation
        })
    
    return result