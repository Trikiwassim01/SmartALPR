import sys
import os
import codecs

# Add the current directory to sys.path so we can import app
current_dir = os.getcwd()
sys.path.append(current_dir)

from app.database import SessionLocal
from app.main import SmartDatabaseTool, ToolRouter

# Configurer stdout pour gerer l'encodage proprement sur Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def debug_history_query():
    print("--- STARTING DEBUG ---")
    db = SessionLocal()
    
    question = "Affiche l'historique"
    print(f"Question: {question}")
    
    # 1. Test SmartDatabaseTool directly
    tool = SmartDatabaseTool(db)
    
    try:
        # We need to monkeypatch the print function or just rely on stdout being captured by run_command
        # The existing code in main.py has print() statements.
        result = tool.process(question, history="")
        print("\n--- RESULTAT FINAL ---")
        
        # Encodage manuel pour eviter les crashs console
        try:
            print(result)
        except UnicodeEncodeError:
            print(result.encode('ascii', 'replace').decode('ascii'))
        
        # Check against error patterns manually
        error_patterns = [
            "aucun résultat trouvé",
            "aucune donnée",
            "pas de résultats",
            "introuvable dans la base",
            "0 lignes",
            "table vide"
        ]
        is_error = any(pattern in result.lower() for pattern in error_patterns)
        print(f"\nEst considere comme erreur ? {is_error}")
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    
    print("--- END DEBUG ---")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    debug_history_query()
