from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models
from ..database import get_db

router = APIRouter()

from fastapi import File, UploadFile
from ..services.license_plate_service import analyze_vehicle_image

@router.post("/analyze-plate")
async def analyze_plate(file: UploadFile = File(...)):
    """
    Analyze uploaded vehicle image to extract license plate
    """
    return await analyze_vehicle_image(file)


@router.post("/", response_model=schemas.Voiture, status_code=201)
def create_voiture(voiture: schemas.VoitureCreate, db: Session = Depends(get_db)):
    """
    Créer une nouvelle voiture
    """
    # Vérifier si la matricule existe déjà
    existing = db.query(models.Voiture).filter(models.Voiture.matricule == voiture.matricule).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cette matricule existe déjà")
    
    # Vérifier si le client existe
    client = db.query(models.Client).filter(models.Client.id == voiture.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    db_voiture = models.Voiture(**voiture.dict())
    db.add(db_voiture)
    db.commit()
    db.refresh(db_voiture)
    return db_voiture

@router.get("/", response_model=List[schemas.Voiture])
def read_voitures(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Récupérer toutes les voitures
    """
    voitures = db.query(models.Voiture).offset(skip).limit(limit).all()
    return voitures

@router.get("/{matricule}", response_model=schemas.Voiture)
def read_voiture(matricule: str, db: Session = Depends(get_db)):
    """
    Récupérer une voiture par sa matricule
    """
    voiture = db.query(models.Voiture).filter(models.Voiture.matricule == matricule).first()
    if voiture is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")
    return voiture

@router.put("/{matricule}", response_model=schemas.Voiture)
def update_voiture(
    matricule: str,
    voiture_update: schemas.VoitureCreate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour une voiture
    """
    voiture = db.query(models.Voiture).filter(models.Voiture.matricule == matricule).first()
    if voiture is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")
    
    # Si changement de matricule, vérifier si nouvelle existe
    if voiture_update.matricule != matricule:
        existing = db.query(models.Voiture).filter(
            models.Voiture.matricule == voiture_update.matricule
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Matricule déjà utilisé")
    
    # Mettre à jour
    for field, value in voiture_update.dict().items():
        setattr(voiture, field, value)
    
    db.commit()
    db.refresh(voiture)
    return voiture

@router.delete("/{matricule}", status_code=204)
def delete_voiture(matricule: str, db: Session = Depends(get_db)):
    """
    Supprimer une voiture
    """
    voiture = db.query(models.Voiture).filter(models.Voiture.matricule == matricule).first()
    if voiture is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")
    
    db.delete(voiture)
    db.commit()
    return None

@router.get("/{matricule}/historiques", response_model=List[schemas.Historique])
def get_voiture_historiques(matricule: str, db: Session = Depends(get_db)):
    """
    Récupérer l'historique d'une voiture
    """
    voiture = db.query(models.Voiture).filter(models.Voiture.matricule == matricule).first()
    if voiture is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")
    
    return voiture.historiques

@router.get("/search/", response_model=List[schemas.Voiture])
def search_voitures(
    matricule: Optional[str] = None,
    modele: Optional[str] = None,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Rechercher des voitures
    """
    query = db.query(models.Voiture)
    
    if matricule:
        query = query.filter(models.Voiture.matricule.ilike(f"%{matricule}%"))
    if modele:
        query = query.filter(models.Voiture.modele.ilike(f"%{modele}%"))
    if client_id:
        query = query.filter(models.Voiture.client_id == client_id)
    
    return query.all()