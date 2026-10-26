import asyncio
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour pouvoir importer app
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag_service import RAGService

async def main():
    service = RAGService()
    
    # On va indexer le dossier 'uploads'
    data_dir = "uploads"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Dossier {data_dir} créé. Veuillez y placer des documents.")
        return

    print(f"Chargement des documents depuis {data_dir}...")
    docs = service.load_all_documents(data_dir)
    
    if not docs:
        print("Aucun document trouvé dans 'uploads'.")
        return
        
    print(f"Traitement de {len(docs)} documents...")
    chunks = service.chunk_documents(docs)
    
    print(f"Génération des embeddings pour {len(chunks)} fragments...")
    embedded = service.embed_chunks(chunks)
    
    print("Stockage dans Supabase...")
    await service.store_in_supabase(embedded)
    
    print("✅ Indexation terminée !")

if __name__ == "__main__":
    asyncio.run(main())
