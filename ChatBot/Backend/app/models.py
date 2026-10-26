from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base

# Table d'association pour la relation Many-to-Many entre Historique et Pièce
historique_piece_association = Table(
    'historique_piece',
    Base.metadata,
    Column('historique_id', Integer, ForeignKey('historiques.id')),
    Column('piece_id', Integer, ForeignKey('pieces.id'))
)

# Table d'association pour la relation Many-to-Many entre Historique et Tarif_Reparation
historique_tarif_association = Table(
    'historique_tarif',
    Base.metadata,
    Column('historique_id', Integer, ForeignKey('historiques.id')),
    Column('tarif_reparation_id', Integer, ForeignKey('tarif_reparations.id'))
)

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    num = Column(String(20), unique=True, index=True)
    
    # Relations
    voitures = relationship("Voiture", back_populates="client")
    factures = relationship("Facture", back_populates="client")

class Voiture(Base):
    __tablename__ = "voitures"
    
    matricule = Column(String(50), primary_key=True, index=True)
    modele = Column(String(100), nullable=False)
    image_voiture = Column(String(255), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    
    # Relations
    client = relationship("Client", back_populates="voitures")
    historiques = relationship("Historique", back_populates="voiture")

class Historique(Base):
    __tablename__ = "historiques"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today)
    details_reparation = Column(Text)
    montant_reparation = Column(Float, default=0.0)
    montant_pieces = Column(Float, default=0.0)
    periode_totale_reparation = Column(Integer)  # en jours
    voiture_matricule = Column(String(50), ForeignKey("voitures.matricule"))
    
    # Relations
    voiture = relationship("Voiture", back_populates="historiques")
    pieces = relationship("Piece", secondary=historique_piece_association, back_populates="historiques")
    tarifs_reparation = relationship("TarifReparation", secondary=historique_tarif_association, back_populates="historiques")
    facture = relationship("Facture", back_populates="historique", uselist=False)

class Facture(Base):
    __tablename__ = "factures"
    
    numero_facture = Column(String(50), primary_key=True, index=True)
    date_facture = Column(Date, default=date.today)
    montant_totale = Column(Float, nullable=False)
    resume_reparation = Column(Text)
    type_paiement = Column(String(50))
    client_id = Column(Integer, ForeignKey("clients.id"))
    historique_id = Column(Integer, ForeignKey("historiques.id"))
    
    # Relations
    client = relationship("Client", back_populates="factures")
    historique = relationship("Historique", back_populates="facture")

class TarifReparation(Base):
    __tablename__ = "tarif_reparations"
    
    id = Column(Integer, primary_key=True, index=True)
    type_reparation = Column(String(100), nullable=False)
    prix = Column(Float, nullable=False)
    periode_reparation = Column(Integer)  # en jours
    
    # Relations
    historiques = relationship("Historique", secondary=historique_tarif_association, back_populates="tarifs_reparation")

class Piece(Base):
    __tablename__ = "pieces"
    
    id = Column(Integer, primary_key=True, index=True)
    nom_piece = Column(String(100), nullable=False)
    quantite = Column(Integer, default=1)
    prix_unitaire = Column(Float, nullable=False)
    
    # Relations
    historiques = relationship("Historique", secondary=historique_piece_association, back_populates="pieces")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String(50), primary_key=True, index=True)
    created_at = Column(Float, default=0.0) # Timestamp
    title = Column(String(100), nullable=True)
    
    # Relations
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey("chat_sessions.id"))
    role = Column(String(20), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(Float, default=0.0)
    
    # Relations
    session = relationship("ChatSession", back_populates="messages")