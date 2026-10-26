from sqlalchemy.orm import Session
from . import models, schemas
from datetime import date

# CRUD pour Client
def create_client(db: Session, client: schemas.ClientCreate):
    db_client = models.Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def get_client(db: Session, client_id: int):
    return db.query(models.Client).filter(models.Client.id == client_id).first()

def get_clients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Client).offset(skip).limit(limit).all()

# CRUD pour Voiture
def create_voiture(db: Session, voiture: schemas.VoitureCreate):
    db_voiture = models.Voiture(**voiture.dict())
    db.add(db_voiture)
    db.commit()
    db.refresh(db_voiture)
    return db_voiture

def get_voiture(db: Session, matricule: str):
    return db.query(models.Voiture).filter(models.Voiture.matricule == matricule).first()

# CRUD pour Piece
def create_piece(db: Session, piece: schemas.PieceCreate):
    db_piece = models.Piece(**piece.dict())
    db.add(db_piece)
    db.commit()
    db.refresh(db_piece)
    return db_piece

# CRUD pour TarifReparation
def create_tarif_reparation(db: Session, tarif: schemas.TarifReparationCreate):
    db_tarif = models.TarifReparation(**tarif.dict())
    db.add(db_tarif)
    db.commit()
    db.refresh(db_tarif)
    return db_tarif

# CRUD pour Historique
def create_historique(db: Session, historique: schemas.HistoriqueCreate):
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
        tarif = db.query(models.TarifReparation).filter(models.TarifReparation.id == tarif_id).first()
        if tarif:
            db_historique.tarifs_reparation.append(tarif)
    
    db.add(db_historique)
    db.commit()
    db.refresh(db_historique)
    return db_historique

# CRUD pour Facture
def create_facture(db: Session, facture: schemas.FactureCreate):
    db_facture = models.Facture(**facture.dict())
    db.add(db_facture)
    db.commit()
    db.refresh(db_facture)
    return db_facture