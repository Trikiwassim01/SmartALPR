from app.database import SessionLocal, engine
from app import models
from sqlalchemy.orm import Session

def seed():
    # Create tables if not exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if clients exist
    if db.query(models.Client).count() == 0:
        print("Seeding Clients...")
        clients = [
            models.Client(nom="Dupont", prenom="Jean", num="0601020304"),
            models.Client(nom="Martin", prenom="Sophie", num="0611223344"),
            models.Client(nom="Dubois", prenom="Pierre", num="0655667788"),
        ]
        db.add_all(clients)
        db.commit()
        
        # Get IDs
        c1 = db.query(models.Client).filter_by(nom="Dupont").first()
        c2 = db.query(models.Client).filter_by(nom="Martin").first()
        c3 = db.query(models.Client).filter_by(nom="Dubois").first()
        
        print("Seeding Vehicles...")
        vehicles = [
            models.Voiture(matricule="AB-123-CD", modele="Peugeot 208", client_id=c1.id),
            models.Voiture(matricule="EF-456-GH", modele="Renault Clio", client_id=c2.id),
            models.Voiture(matricule="XY-999-ZZ", modele="BMW Serie 3", client_id=c3.id),
            models.Voiture(matricule="AA-000-BB", modele="Tesla Model 3", client_id=c1.id),
        ]
        db.add_all(vehicles)
        db.commit()
        print("✅ Data seeded successfully.")
    else:
        print("Data already exists.")
        
    db.close()

if __name__ == "__main__":
    seed()
