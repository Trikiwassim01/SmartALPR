from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# Schémas pour Client
class ClientBase(BaseModel):
    nom: str
    prenom: str
    num: str

class ClientCreate(ClientBase):
    pass

class Client(ClientBase):
    id: int
    
    class Config:
        from_attributes = True

# Schémas pour Voiture
class VoitureBase(BaseModel):
    matricule: str
    modele: str
    image_voiture: Optional[str] = None
    client_id: int

class VoitureCreate(VoitureBase):
    pass

class Voiture(VoitureBase):
    class Config:
        from_attributes = True

# Schémas pour Piece
class PieceBase(BaseModel):
    nom_piece: str
    quantite: int
    prix_unitaire: float

class PieceCreate(PieceBase):
    pass

class Piece(PieceBase):
    id: int
    
    class Config:
        from_attributes = True

# Schémas pour TarifReparation
class TarifReparationBase(BaseModel):
    type_reparation: str
    prix: float
    periode_reparation: int

class TarifReparationCreate(TarifReparationBase):
    pass

class TarifReparation(TarifReparationBase):
    id: int
    
    class Config:
        from_attributes = True

# Schémas pour Historique
class HistoriqueBase(BaseModel):
    details_reparation: str
    montant_reparation: Optional[float] = 0.0
    montant_pieces: Optional[float] = 0.0
    periode_totale_reparation: Optional[int] = 0
    voiture_matricule: str
    piece_ids: Optional[List[int]] = []
    tarif_ids: Optional[List[int]] = []

class HistoriqueCreate(HistoriqueBase):
    pass

class Historique(HistoriqueBase):
    id: int
    date: date
    
    class Config:
        from_attributes = True

# Schémas pour Facture
class FactureBase(BaseModel):
    numero_facture: str
    montant_totale: float
    resume_reparation: str
    type_paiement: str
    client_id: int
    historique_id: int

class FactureCreate(FactureBase):
    pass

class Facture(FactureBase):
    date_facture: date
    
    class Config:
        from_attributes = True