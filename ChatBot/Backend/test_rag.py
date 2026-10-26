"""
Script de test pour vérifier le système RAG avec Supabase
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent))

from app.services.rag_service import RAGService

async def test_connection():
    """Teste la connexion à Supabase"""
    print("=" * 50)
    print("TEST 1: Connexion à Supabase")
    print("=" * 50)
    
    service = RAGService()
    
    if service.supabase:
        print("✅ Connexion réussie!")
        print(f"   URL: {service.supabase_url}")
    else:
        print("❌ Échec de connexion")
        print("   Vérifiez vos credentials dans .env")
        return False
    
    return True

async def test_search():
    """Teste la recherche de similarité"""
    print("\n" + "=" * 50)
    print("TEST 2: Recherche de similarité")
    print("=" * 50)
    
    service = RAGService()
    
    # Recherche de test
    query = "entretien voiture"
    print(f"Recherche: '{query}'")
    
    try:
        results = service.search_similar(query, limit=3)
        
        if results:
            print(f"✅ Trouvé {len(results)} résultats:")
            for i, res in enumerate(results, 1):
                content = res.get("content", "")[:100] + "..."
                print(f"\n   {i}. {content}")
                print(f"      Metadata: {res.get('metadata', {})}")
        else:
            print("⚠️ Aucun résultat trouvé")
            print("   La base est peut-être vide. Exécutez index_documents.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def test_embedding():
    """Teste la génération d'embeddings"""
    print("\n" + "=" * 50)
    print("TEST 3: Génération d'embeddings")
    print("=" * 50)
    
    service = RAGService()
    
    test_text = "Ceci est un test"
    print(f"Texte: '{test_text}'")
    
    try:
        embedding = service.embeddings.embed_query(test_text)
        print(f"✅ Embedding généré!")
        print(f"   Dimension: {len(embedding)}")
        print(f"   Premiers éléments: {embedding[:5]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def main():
    print("🔍 Tests du système RAG\n")
    
    # Test 1: Connexion
    if not await test_connection():
        print("\n❌ Arrêt des tests (connexion échouée)")
        return
    
    # Test 2: Embedding
    if not await test_embedding():
        print("\n❌ Arrêt des tests (embedding échoué)")
        return
    
    # Test 3: Recherche
    await test_search()
    
    print("\n" + "=" * 50)
    print("Tests terminés!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
