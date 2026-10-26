from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from datetime import date
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from pydantic import BaseModel
from groq import Groq
import re
import time
import json
from typing import Dict, List, Optional, Any
import pandas as pd
from io import StringIO
from sqlalchemy import text
from fastapi import UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fpdf import FPDF
import shutil
from tavily import TavilyClient
from pypdf import PdfReader


from .database import engine, get_db
from . import models

# Charger les variables d'environnement
load_dotenv()

# Modèles de données
class AskRequest(BaseModel):
    session_id: str
    question: str

class AskResponse(BaseModel):
    question: str
    answer: str
    source: str

# Configuration Groq AI
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

def call_groq(prompt: str) -> str:
    """Appel générique à Groq LLM"""
    if not client:
        raise Exception("Client Groq non initialisé")
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=1,
            max_completion_tokens=8192,
            top_p=1,
            stop=None,
            # removed reasoning_effort to be safe, unless sure it works. 
            # User snippet had it, but standard calls might fail if model doesn't support.
            # I will assume standard usage first.
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise Exception(f"Erreur Groq: {str(e)}")

# Mémoire de conversation
# Mémoire de conversation (Gérée par BDD maintenant)
# conversation_memory = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie de l'application"""
    print("[INFO] Demarrage de l'application Garage Management")
    
    # Créer les tables
    models.Base.metadata.create_all(bind=engine)
    print("[INFO] Tables MySQL creees/verifiees")
    
    # Vérifier Groq AI
    if GROQ_API_KEY:
        print("[INFO] Groq API configuree")
    else:
        print("⚠️ GROQ_API_KEY non configurée - Le chat IA ne fonctionnera pas")
    
    yield
    
    print("[INFO] Arret de l'application")

app = FastAPI(
    title="Garage Management API",
    description="API de gestion de garage avec assistant intelligent",
    version="2.0.0",
    lifespan=lifespan
)

# Manager de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajout pour éviter circular dependency si nécessaire
# Mais ici on est dans main.py
from datetime import date

def extract_sql_from_text(text: str) -> str:
    """Extrait le SQL d'une réponse"""
    if not isinstance(text, str):
        return ""
    
    text = text.strip()
    
    # Extraire le bloc SQL
    sql_match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    sql_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    return text.strip()

def execute_sql_query(sql: str, db: Session) -> pd.DataFrame:
    """
    Exécute une requête SQL et retourne un DataFrame
    """
    sql = extract_sql_from_text(sql)
    
    if not sql:
        raise ValueError("❌ Aucune requête SQL valide trouvée")
    
    # Nettoyage
    sql = sql.strip()
    
    # Ajouter un point-virgule si manquant
    if not sql.endswith(';'):
        sql += ';'
    
    print(f"Execution SQL: {sql[:100]}...")
    
    try:
        # Convertir en objet text() de SQLAlchemy
        sql_text = text(sql)
        
        # Exécuter la requête
        result = db.execute(sql_text)
        
        # Détecter le type de requête
        sql_lower = sql.lower()
        
        if sql_lower.startswith(("select", "with", "show", "describe", "explain")):
            # Requête de lecture
            rows = result.fetchall()
            
            if result.returns_rows:
                cols = result.keys()
                
                # Créer un DataFrame
                df = pd.DataFrame(rows, columns=cols)
                
                # Si pas de résultats, créer un DataFrame vide avec les colonnes
                if df.empty:
                    df = pd.DataFrame(columns=cols)
                
                return df
            else:
                return pd.DataFrame({"message": ["Requete executee (pas de resultats)"]})
        
        else:
            # Requête de modification
            db.commit()
            
            # Créer un DataFrame avec le résultat de la commande
            try:
                rowcount = result.rowcount
                if rowcount == -1:
                    message = f"✅ Commande exécutée avec succès: {sql[:50]}..."
                else:
                    message = f"✅ Commande exécutée. {rowcount} ligne(s) affectée(s)."
            except:
                message = f"✅ Commande exécutée avec succès: {sql[:50]}..."
            
            return pd.DataFrame({"message": [message]})
    
    except Exception as e:
        db.rollback()
        error_detail = str(e)
        
        # Messages d'erreur plus explicites
        if "Duplicate entry" in error_detail:
            raise Exception(f"❌ Erreur: Entrée en double. La valeur existe déjà dans la base.")
        elif "foreign key constraint fails" in error_detail:
            raise Exception(f"❌ Erreur de clé étrangère. Vérifiez que les références existent.")
        elif "doesn't exist" in error_detail:
            raise Exception(f"❌ Erreur: La table ou colonne n'existe pas.")
        else:
            raise Exception(f"❌ Erreur SQL: {error_detail}")

def format_dataframe_to_natural_language(df: pd.DataFrame, original_question: str) -> str:
    """
    Convertit les résultats d'un DataFrame en langage naturel
    """
    if df.empty:
        return "Aucun résultat trouvé."
    
    # Si c'est juste un message de succès
    if 'message' in df.columns and len(df) == 1:
        return df.iloc[0]['message']
    
    # Préparer le prompt pour la reformulation
    prompt = f"""Tu es un assistant qui explique les résultats d'une base de données en langage naturel.

Question originale de l'utilisateur: "{original_question}"

Voici les données brutes (premières lignes):
{df.head().to_string()}

Nombre total de lignes: {len(df)}
Colonnes disponibles: {', '.join(df.columns.tolist())}

Instructions:
1. Analyse les données et réponds à la question originale
2. Explique de même langage que la question
3. Donne des insights intéressants si possible
4. Sois concis mais informatif
5. Ne mentionne pas les colonnes techniques comme 'id' sauf si nécessaire
6. Formate les nombres (ex: 1000 → 1 000)

Réponds uniquement avec l'explication en langage naturel:
"""
    
    try:
        response = call_groq(prompt)
        return response.strip()
    except:
        # Fallback si Gemini échoue
        if len(df) == 1 and len(df.columns) == 1:
            # Cas simple : une seule valeur
            value = df.iloc[0, 0]
            return f"Le résultat est : {value}"
        elif len(df) <= 5:
            # Petit tableau : formater manuellement
            lines = []
            for idx, row in df.iterrows():
                if len(df) == 1:
                    lines.append(f"Résultat : {', '.join([str(v) for v in row.values])}")
                else:
                    lines.append(f"- {', '.join([str(v) for v in row.values])}")
            return "\n".join(lines)
        else:
            return f"J'ai trouvé {len(df)} résultats. Voici un résumé."

def analyze_question_type(question: str) -> Dict[str, bool]:
    """
    Analyse le type de question pour déterminer quelle tool utiliser
    """
    question_lower = question.lower()
    
    # Mots-clés pour différents types de requêtes
    keywords = {
        "sql_direct": ["sql", "requête sql", "exécute", "select", "insert", "update", "delete", "crée", "supprime"],
        "data_analysis": ["combien", "nombre", "total", "moyenne", "somme", "statistique", "analyse", "rapport"],
        "client_info": ["client", "clients", "clientèle", "nom", "prénom", "téléphone"],
        "voiture_info": ["voiture", "voitures", "matricule", "modèle", "véhicule"],
        "facture_info": ["facture", "factures", "paiement", "montant", "tarif"],
        "reparation_info": ["réparation", "réparations", "historique", "maintenance", "pièce", "intervention", "interventions", "travaux", "service", "entretien", "dernière", "dernières", "derniers", "passé", "précédent", "liste", "affiche", "montre", "voir", "quelles", "quels"],
        "policy_info": ["politique", "règle", "procédure", "comment", "peut-on", "est-ce que"],
        "summary": ["résumé", "synthèse", "overview", "état", "situation"],
        "web_search": ["recherche", "trouve", "cherche", "actualité", "news", "prix", "information sur", "internet"],
        "doc_search": ["guide", "manuel", "entretien", "volkswagen", "vw", "vidange", "révision", "huile", "courroie", "filtre", "frein", "pneu", "pression", "technique", "plan", "calendrier", "kilométrage", "changement", "essuie-glace", "balai", "lame", "pare-brise", "liquide", "ampoule", "batterie", "symptôme", "indication"]
    }
    
    analysis = {key: False for key in keywords}
    
    for key, words in keywords.items():
        for word in words:
            if word in question_lower:
                analysis[key] = True
                break
    
    return analysis

def generate_sql_from_natural_language(question: str, question_type: Dict[str, bool], history: str = "") -> str:
    """
    Génère une requête SQL à partir d'une question en langage naturel
    Utilise l'historique de conversation pour le contexte
    """
    # Schéma de la base
    schema = """
    SCHEMA de la base de données 'garage_db':
    
    TABLES et COLONNES:
    1. clients: id, nom, prenom, num
    2. voitures: matricule, modele, image_voiture, client_id
    3. historiques: id, date, details_reparation, montant_reparation, montant_pieces, periode_totale_reparation, voiture_matricule
    4. factures: numero_facture, date_facture, montant_totale, resume_reparation, type_paiement, client_id, historique_id
    5. pieces: id, nom_piece, quantite, prix_unitaire
    6. tarif_reparations: id, type_reparation, prix, periode_reparation
    
    RELATIONS:
    - Un client peut avoir plusieurs voitures (clients.id → voitures.client_id)
    - Une voiture peut avoir plusieurs historiques (voitures.matricule → historiques.voiture_matricule)
    - Un historique peut avoir une facture (historiques.id → factures.historique_id)
    - Un client peut avoir plusieurs factures (clients.id → factures.client_id)
    - Historique peut avoir plusieurs pièces (relation many-to-many via historique_piece)
    - Historique peut avoir plusieurs tarifs (relation many-to-many via historique_tarif)
    """
    
    # Ajouter le contexte si fourni
    context_section = ""
    if 'history' in locals() and history:
        context_section = f"\n\nCONTEXTE DE LA CONVERSATION:\n{history}\n"
    
    prompt = f"""{schema}

Question de l'utilisateur : "{question}"
{context_section}
Analyse du type de question: {json.dumps(question_type, ensure_ascii=False)}

INSTRUCTIONS TRÈS IMPORTANTES:
1. Génère UNIQUEMENT UNE SEULE requête SQL MySQL complète et valide
2. N'ajoute AUCUN texte explicatif, aucun markdown, aucun backtick
3. Utilise des alias explicites pour les colonnes SELECT
4. Inclus les jointures nécessaires pour les SELECT
5. Ordonne les résultats quand c'est pertinent (ORDER BY)
6. Limite les résultats si nécessaire (LIMIT 10)
7. INTERDIT ABSOLU: Ne génère JAMAIS plusieurs instructions SQL séparées par point-virgule
8. AUTORISÉ: INSERT, UPDATE, DELETE, SELECT - mais UNE SEULE à la fois
9. Si des informations critiques manquent (ex: quel client exactement?), génère: SELECT 'INFO_MANQUANTE: <question précise>' as message;
10. Pour INSERT/UPDATE, utilise des sous-requêtes SELECT si nécessaire pour trouver les IDs

Exemples:
- "Combien de clients ?" → SELECT COUNT(*) as nombre_clients FROM clients;
- "Affiche les réparations" → SELECT h.date, h.details_reparation, v.matricule FROM historiques h JOIN voitures v ON h.voiture_matricule = v.matricule ORDER BY h.date DESC LIMIT 10;
- "Crée un client Jean Dupont 0612345678" → INSERT INTO clients (nom, prenom, num) VALUES ('Dupont', 'Jean', '0612345678');
- "J'ai fait une réparation moteur pour la voiture AB-123-CD, pièces 700dt, 4 jours" → INSERT INTO historiques (date, details_reparation, montant_pieces, periode_totale_reparation, voiture_matricule) VALUES (CURDATE(), 'Réparation moteur', 700, 4, 'AB-123-CD');
- "Réparation pour Mohamed Chakroun" → SELECT 'INFO_MANQUANTE: Quelle est la matricule du véhicule de Mohamed Chakroun ?' as message;

EXEMPLES SPÉCIFIQUES POUR L'HISTORIQUE:
- "Historique du client Jean Dupont" → SELECT h.date, h.details_reparation, h.montant_reparation, h.montant_pieces, v.matricule, v.modele FROM historiques h JOIN voitures v ON h.voiture_matricule = v.matricule JOIN clients c ON v.client_id = c.id WHERE c.nom LIKE '%Dupont%' AND c.prenom LIKE '%Jean%' ORDER BY h.date DESC;
- "Historique de la voiture 123 TN 4567" → SELECT h.date, h.details_reparation, h.montant_reparation, h.montant_pieces, h.periode_totale_reparation FROM historiques h WHERE h.voiture_matricule = '123 TN 4567' ORDER BY h.date DESC;
- "Dernières réparations" → SELECT h.date, h.details_reparation, v.matricule, c.nom, c.prenom, (h.montant_reparation + h.montant_pieces) as total FROM historiques h JOIN voitures v ON h.voiture_matricule = v.matricule JOIN clients c ON v.client_id = c.id ORDER BY h.date DESC LIMIT 10;
- "Combien de réparations pour Mohamed" → SELECT COUNT(*) as nombre_reparations, SUM(h.montant_reparation + h.montant_pieces) as total_depense FROM historiques h JOIN voitures v ON h.voiture_matricule = v.matricule JOIN clients c ON v.client_id = c.id WHERE c.prenom LIKE '%Mohamed%';

Génère maintenant la requête SQL pour: "{question}"
"""
    
    try:
        sql = call_groq(prompt)
        
        # Nettoyer la réponse
        sql = extract_sql_from_text(sql)
        
        return sql
    
    except Exception as e:
        raise Exception(f"❌ Erreur de génération SQL: {str(e)}")

def get_conversation_history(session_id: str, db: Session) -> str:
    """Récupère l'historique de conversation depuis la BDD"""
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session_id
    ).order_by(models.ChatMessage.timestamp).limit(10).all()
    
    formatted_history = []
    for msg in messages:
        role_display = "Utilisateur" if msg.role == "user" else "Assistant"
        formatted_history.append(f"{role_display}: {msg.content}")
    
    return "\n".join(formatted_history)

def add_to_conversation(session_id: str, role: str, content: str, db: Session):
    """Ajoute un message à la conversation en BDD"""
    # Vérifier si la session existe, sinon la créer
    chat_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not chat_session:
        chat_session = models.ChatSession(id=session_id, created_at=time.time(), title=f"Session {session_id[:8]}")
        db.add(chat_session)
        db.commit()
    
    # Créer le message
    new_message = models.ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        timestamp=time.time()
    )
    db.add(new_message)
    db.commit()

# ============================================================================
# SYSTEME DE TOOLS INTELLIGENT
# ============================================================================

class SmartDatabaseTool:
    """Tool intelligente qui comprend le langage naturel et exécute SQL"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def process(self, question: str, history: str = "") -> str:
        """
        Traite une question en langage naturel:
        1. Analyse le type de question
        2. Génère la requête SQL
        3. Exécute la requête
        4. Reformule les résultats en langage naturel
        Utilise l'historique pour le contexte
        """
        try:
            print(f"Traite question: {question}")
            
            # Étape 1: Analyser le type de question
            question_type = analyze_question_type(question)
            print(f"Type detecte: {question_type}")
            
            # Étape 2: Générer la requête SQL avec contexte
            print("Generation requete SQL...")
            sql_query = generate_sql_from_natural_language(question, question_type, history)
            print(f"Requete SQL: {sql_query[:200]}...")
            
            # Étape 3: Exécuter la requête
            print("Execution requete...")
            df_result = execute_sql_query(sql_query, self.db)
            print(f"Resultats: {len(df_result)} lignes")
            
            # Étape 4: Reformuler en langage naturel
            print("Reformulation...")
            natural_language_result = format_dataframe_to_natural_language(df_result, question)
            
            # Ajouter la requête SQL en note si c'est pertinent
            if not df_result.empty and 'message' not in df_result.columns:
                result = f"{natural_language_result}\n\n(Requete SQL: {sql_query[:100]}...)"
            else:
                result = natural_language_result
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"Erreur technique: {error_msg}")
            
            # Convertir les erreurs techniques en messages utilisateurs friendly
            if "syntax error" in error_msg.lower() or "1064" in error_msg:
                return "Je n'ai pas pu exécuter cette opération. Pouvez-vous reformuler votre demande de manière plus simple ou en plusieurs étapes ?"
            elif "foreign key" in error_msg.lower():
                return "Cette opération nécessite des informations liées. Pouvez-vous vérifier que le client ou le véhicule existe ?"
            elif "duplicate" in error_msg.lower():
                return "Cette entrée existe déjà dans la base de données. Voulez-vous la modifier plutôt ?"
            elif "doesn't exist" in error_msg.lower() or "unknown" in error_msg.lower():
                return "Je ne trouve pas cette information dans la base. Pouvez-vous vérifier les détails ?"
            else:
                return "Je n'ai pas pu traiter cette demande. Pouvez-vous la reformuler différemment ou me donner plus de détails ?"

class PolicyTool:
    """Tool pour les questions sur les politiques et règles"""
    
    def __init__(self):
        self.policies = {
            "remise": "Remise de 15% pour les clients fidèles (plus de 5 réparations)",
            "garantie": "Garantie de 6 mois sur les réparations et pièces",
            "paiement": "Paiement accepté: espèces, carte, virement. Délai de paiement: 30 jours",
            "annulation": "Annulation gratuite jusqu'à 24h avant le rendez-vous",
            "urgence": "Service d'urgence disponible avec majoration de 30%",
            "livraison": "Service de livraison gratuit dans un rayon de 20km"
        }
    
    def process(self, question: str, history: str = "") -> str:
        """Répond aux questions sur les politiques en tenant compte du contexte"""
        question_lower = question.lower()
        
        for key, policy in self.policies.items():
            if key in question_lower:
                return f"📋 Politique '{key}': {policy}"
        
        # Si aucune politique ne correspond, utiliser Groq
        try:
            response = call_groq(f"""
Tu es un assistant IA spécialisé dans la gestion d’un garage automobile.
Tu assistes le mécanicien dans ses tâches quotidiennes de gestion et de suivi.

L’utilisateur demande : "{question}"

Fonctionnalités disponibles pour le mécanicien :
- Effectuer les opérations CRUD (Créer, Lire, Mettre à jour, Supprimer) sur les clients
- Effectuer les opérations CRUD sur les véhicules
- Consulter l’historique des interventions d’un véhicule
- Consulter l’historique des services d’un client
- Générer une facture claire et détaillée (client, véhicule, services, coût total)

Règles de réponse :
- Réponds dans la même langue que la question de l’utilisateur
- Utilise un ton clair, professionnel et concis
- Si la demande dépasse les fonctionnalités du garage ou ne concerne pas la gestion automobile, explique-le poliment
- Si des informations sont manquantes, demande UNIQUEMENT l'information nécessaire de manière concise (ex: "Quel est l'ID du client ?")
- Ne fais aucune supposition non justifiée

Objectif :
Fournir une aide fiable, structurée et efficace au mécanicien afin de faciliter la gestion du garage.
""")

            
            return response.strip()
        
        except:
            return "Je ne trouve pas d'information spécifique sur cette question. Pouvez-vous reformuler ?"

class WebSearchTool:
    """Outil pour rechercher des informations sur le web avec Tavily"""
    
    def __init__(self):
        self.tavily_client = TavilyClient("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")
    
    def process(self, question: str, history: str = "") -> str:
        """Effectue une recherche web et synthétise les résultats"""
        try:
            print(f"🌐 Recherche web Tavily: {question}")
            
            # Recherche avec Tavily
            response = self.tavily_client.search(
                query=question,
                search_depth="advanced",
                max_results=5
            )
            
            # Analyser et synthétiser les résultats avec Groq
            if response.get("results"):
                # Préparer les résultats pour le résumé
                results_text = ""
                for i, result in enumerate(response["results"][:5], 1):
                    results_text += f"{i}. {result.get('title', '')}\n"
                    results_text += f"   {result.get('content', '')}\n\n"
                
                # Demander à Groq de faire un résumé concis
                synthesis_prompt = f"""Question: "{question}"

Résultats de recherche:
{results_text}

INSTRUCTIONS:
- Fais un résumé COURT et DIRECT (maximum 3-4 phrases)
- Va droit à l'essentiel, pas d'introduction
- Réponds dans la même langue que la question
- Ne cite PAS les sources dans le résumé (elles seront listées séparément)
- N'utilise PAS de gras (étoiles) dans le résumé

Résumé:"""

                summary = call_groq(synthesis_prompt).strip()
                
                # Construire la réponse finale avec le résumé + meilleure source seulement
                final_response = summary + "\n\n"
                
                # Ajouter uniquement la première source (la plus pertinente)
                if response["results"]:
                    best_result = response["results"][0]
                    title = best_result.get('title', 'Sans titre')
                    url = best_result.get('url', '')
                    final_response += f"📚 Source: [{title}]({url})\n"
                
                return final_response
            else:
                return "Aucun résultat trouvé pour cette recherche."
                
        except Exception as e:
            print(f"❌ Erreur recherche web: {str(e)}")
            return "Je ne peux pas effectuer de recherche web pour le moment."






from .services.rag_service import RAGService

class KnowledgeTool:
    """Outil RAG pour interroger les documents (PDF, Word, Excel, etc.) via Supabase"""
    
    def __init__(self, data_dir: str = "uploads"):
        self.rag_service = RAGService()
        self.data_dir = data_dir
        # On pourrait déclencher l'indexation ici, mais c'est lourd au démarrage
        # Pour l'instant on suppose que les données sont déjà dans Supabase
        
    def process(self, question: str, history: str = "") -> str:
        """Répond à une question en utilisant le vector store Supabase"""
        results = self.rag_service.search_similar(question, limit=4)
        
        if not results:
            return "Je n'ai pas trouvé d'information pertinente dans mes documents pour cette question."
            
        # Construire le contexte
        context = ""
        sources = set()
        for res in results:
            content = res.get("content", "")
            metadata = res.get("metadata", {})
            source = metadata.get("source", "Document inconnu")
            context += f"\n--- {source} ---\n{content}\n"
            sources.add(source)
            
        prompt = f"""Tu es un expert technique du garage. Utilise les informations suivantes pour répondre.
Si l'information n'est pas dans le contexte, dis-le clairement.

CONTEXTE:
{context}

QUESTION: "{question}"

INSTRUCTIONS:
- Réponds de manière COMPLÈTE, DÉTAILLÉE et PÉDAGOGIQUE
- Explique bien les concepts et inclus tous les détails pertinents du contexte
- Ne sois PAS trop bref, l'utilisateur souhaite une explication approfondie
- Ne cite PAS les sources dans le texte
- Réponds dans la même langue que la question

RÉPONSE:"""

        answer = call_groq(prompt).strip()
        
        # Formater la réponse finale
        final_response = answer + "\n\n"
        final_response += "ℹ️ *Réponse générée à partir des documents internes (RAG)*\n\n"
        final_response += "**📚 Sources Documentaires:**\n"
        for source in sorted(sources):
            # Nettoyer le chemin si nécessaire
            source_name = os.path.basename(source) if "/" in source or "\\" in source else source
            final_response += f"- {source_name}\n"
            
        return final_response

class SummaryTool:
    """Tool pour générer des résumés et synthèses"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def process(self, question: str) -> str:
        """Génère un résumé des données"""
        try:
            # Requêtes pour obtenir un résumé
            queries = {
                "clients": "SELECT COUNT(*) as nombre_clients FROM clients",
                "voitures": "SELECT COUNT(*) as nombre_voitures FROM voitures",
                "reparations_mois": """
                    SELECT COUNT(*) as reparations_ce_mois 
                    FROM historiques 
                    WHERE MONTH(date) = MONTH(CURRENT_DATE) 
                    AND YEAR(date) = YEAR(CURRENT_DATE)
                """,
                "chiffre_affaires": """
                    SELECT SUM(montant_totale) as chiffre_affaires_mois
                    FROM factures 
                    WHERE MONTH(date_facture) = MONTH(CURRENT_DATE) 
                    AND YEAR(date_facture) = YEAR(CURRENT_DATE)
                """,
                "clients_fideles": """
                    SELECT c.nom, c.prenom, COUNT(h.id) as nombre_reparations
                    FROM clients c 
                    JOIN voitures v ON c.id = v.client_id 
                    JOIN historiques h ON v.matricule = h.voiture_matricule
                    GROUP BY c.id 
                    HAVING COUNT(h.id) >= 3
                    ORDER BY nombre_reparations DESC 
                    LIMIT 5
                """
            }
            
            results = {}
            for key, query in queries.items():
                try:
                    df = execute_sql_query(query, self.db)
                    if not df.empty:
                        results[key] = df.iloc[0, 0] if len(df.columns) == 1 else df
                except:
                    results[key] = "N/A"
            
            # Générer le résumé avec Gemini
            prompt = f"""Génère un résumé professionnel de même langage que la question pour le garage.

Données actuelles:
- Nombre total de clients: {results.get('clients', 'N/A')}
- Nombre total de voitures enregistrées: {results.get('voitures', 'N/A')}
- Réparations ce mois-ci: {results.get('reparations_mois', 'N/A')}
- Chiffre d'affaires ce mois: {results.get('chiffre_affaires', 'N/A')} €

Question de l'utilisateur: "{question}"

Crée un résumé concis, professionnel et informatif de même langage que la question.
"""
            
            response = call_groq(prompt)
            
            return response.strip()
        
        except Exception as e:
            return f"❌ Erreur dans le résumé: {str(e)}"

# ============================================================================
# ROUTEUR INTELLIGENT POUR LES TOOLS
# ============================================================================

class ToolRouter:
    """Route les questions vers la tool appropriée"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.tools = {
            "database": SmartDatabaseTool(db_session),
            "policy": PolicyTool(),
            "summary": SummaryTool(db_session),
            "web_search": WebSearchTool(),
            "knowledge": KnowledgeTool() # Nouvel outil RAG Supabase
        }
    
    def route_question(self, question: str, session_id: str, history: str = "") -> str:
        """
        Analyse la question et route vers la tool appropriée
        Passe l'historique aux outils pour le contexte
        """
        # Analyser le type de question
        question_type = analyze_question_type(question)
        
        # PRIORITÉ 1: Router vers le guide PDF pour les questions techniques/entretien
        if question_type["doc_search"]:
            print("🛠️ Utilisation de KnowledgeTool")
            return self.tools["knowledge"].process(question, history)

        # PRIORITÉ 2: Router vers la recherche web
        if question_type["web_search"] and not (question_type["client_info"] or question_type["voiture_info"]):
            print("🛠️ Utilisation de WebSearchTool")
            return self.tools["web_search"].process(question, history)
        
        # Déterminer quelle tool utiliser
        if question_type["policy_info"]:
            print("🛠️ Utilisation de PolicyTool")
            return self.tools["policy"].process(question, history)
        
        elif question_type["summary"]:
            print("🛠️ Utilisation de SummaryTool")
            return self.tools["summary"].process(question)
        
        else:
            # Par défaut, utiliser la tool de base de données
            print("🛠️ Utilisation de SmartDatabaseTool")
            db_response = self.tools["database"].process(question, history)
            
            # Vérifier si c'est vraiment une erreur de données (pas juste une phrase avec "aucun")
            # On vérifie si c'est un message d'erreur SQL ou vraiment aucun résultat trouvé
            error_patterns = [
                "aucun résultat trouvé",
                "aucune donnée",
                "pas de résultats",
                "introuvable dans la base",
                "0 lignes",
                "table vide"
            ]
            
            is_empty_result = any(pattern in db_response.lower() for pattern in error_patterns)
            
            if is_empty_result:
                # Si la question porte clairement sur des données clients/véhicules, on confirme l'absence plutôt que d'être vague
                if question_type["client_info"] or question_type["voiture_info"] or question_type["reparation_info"] or question_type["facture_info"]:
                    return "Je n'ai trouvé aucune information correspondante dans la base de données. Il n'y a probablement pas d'historique ou d'enregistrement pour cette demande."

                # Pas de réponse - rediriger vers sources disponibles
                return """Je n'ai pas trouvé cette information dans mes sources disponibles.

**Sources que je peux consulter :**
- 📊 Base de données (clients, véhicules, réparations, factures)
- 📘 Guide d'entretien Volkswagen
- 🌐 Recherche web (si nécessaire)

Pouvez-vous reformuler votre question ou préciser ce que vous recherchez ?"""
            
            return db_response

# ============================================================================
# FONCTION PRINCIPALE DE GÉNÉRATION DE RÉPONSE
# ============================================================================

def generate_intelligent_response(question: str, session_id: str, db: Session) -> str:
    """Génère une réponse intelligente en utilisant le système de tools"""
    if not GROQ_API_KEY:
        return "⚠️ Service d'IA non disponible. Configurez GROQ_API_KEY dans le fichier .env"
    
    try:
        # Initialiser le routeur de tools
        router = ToolRouter(db)
        
        # Obtenir l'historique
        history = get_conversation_history(session_id, db)
        
        # Analyser si on a besoin de contexte supplémentaire
        prompt = f"""Tu es un assistant intelligent pour un système de gestion de garage.

Historique de la conversation:
{history}

Question actuelle: "{question}"

Analyse rapide:
1. Est-ce une question technique sur la base de données?
2. Est-ce une question sur les politiques/procédures?
3. Est-ce une demande de résumé/synthèse?
4. Est-ce une conversation générale?

Réponds uniquement par:
- "DATABASE" si c'est une requête sur les clients, factures, RDV ou historique
- "KNOWLEDGE" si c'est une question sur l'entretien, les pannes, les pièces, les procédures techniques, un voyant allumé, ou toute info générale sur les voitures
- "CHAT" UNIQUEMENT pour les salutations (bonjour, merci) ou les questions hors-sujet
NOTE: Si la question porte sur "comment faire", "c'est quoi", "pourquoi", "quand changer" -> C'EST KNOWLEDGE
"""
        
        classification = call_groq(prompt).strip().upper()
        
        print(f"🤖 Classification: {classification}")
        
        if classification == "CHAT":
            # Conversation générale - utiliser Groq directement
            chat_prompt = f"""Tu es un assistant pour un garage automobile.
            
Historique:
{history}

Question: "{question}"

Réponds de manière utile, amicale et professionnelle de même langage que la question.
"""
            final_answer = call_groq(chat_prompt).strip()
            
        elif classification == "KNOWLEDGE":
            # Router vers KnowledgeTool explicitement
            print("🤖 Classification KNOWLEDGE -> KnowledgeTool")
            final_answer = router.tools["knowledge"].process(question, history)
        
        else:
            # Utiliser le système de tools avec historique
            final_answer = router.route_question(question, session_id, history)
        
        # Ajouter à l'historique
        add_to_conversation(session_id, "user", question, db)
        add_to_conversation(session_id, "assistant", final_answer, db)
        
        return final_answer
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Erreur dans generate_intelligent_response: {error_msg}")
        
        # Fallback: toujours donner une réponse utilisable
        try:
            fallback_prompt = f"""L'utilisateur a demandé: "{question}"
            
Réponds de manière professionnelle en demandant poliment plus de précisions ou en proposant une alternative.
Ne mentionne JAMAIS d'erreur technique.
Réponds dans la même langue que la question."""
            return call_groq(fallback_prompt).strip()
        except:
            return "Je n'ai pas bien compris votre demande. Pouvez-vous me donner plus de détails ou reformuler ?"

# ============================================================================
# ENDPOINTS API
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "🏎️ Garage Management API Intelligente",
        "version": "2.0.0",
        "features": [
            "Assistant IA avec compréhension contextuelle",
            "Système de tools intelligent",
            "Reformulation des résultats en langage naturel",
            "Accès SQL complet avec sécurité",
            "Base de données MySQL"
        ],
        "tools_available": [
            "SmartDatabaseTool: Convertit langage naturel → SQL → Résultats naturels",
            "PolicyTool: Répond aux questions sur les règles",
            "SummaryTool: Génère des résumés et synthèses"
        ],
        "endpoints": {
            "chat_intelligent": "POST /ask",
            "sql_direct": "POST /sql",
            "analyse_question": "POST /analyze",
            "health": "GET /health",
            "tables": "GET /tables",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "MySQL",
        "ai_service": "Groq (OpenAI GPT-OSS-120B)",
        "tools_loaded": True,
        "timestamp": time.time()
    }

@app.get("/tables")
async def list_tables(db: Session = Depends(get_db)):
    """Lister toutes les tables de la base"""
    try:
        result = db.execute("SHOW TABLES")
        tables = [row[0] for row in result.fetchall()]
        
        return {
            "database": "garage_db",
            "tables": tables,
            "total_tables": len(tables)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db)
):
    """
    Pose une question à l'assistant IA intelligent
    Le système choisit automatiquement la tool appropriée
    """
    start_time = time.time()
    
    try:
        print(f"Question recue [{request.session_id}]: {request.question}")
        
        # Générer la réponse intelligente
        answer = generate_intelligent_response(request.question, request.session_id, db)
        
        elapsed = time.time() - start_time
        
        print(f"Reponse generee en {elapsed:.2f}s")
        
        return AskResponse(
            question=request.question,
            answer=answer,
            source="intelligent_agent"
        )
    
    except Exception as e:
        error_msg = f"❌ Erreur: {str(e)}"
        print(error_msg)
        return AskResponse(
            question=request.question,
            answer=error_msg,
            source="error"
        )

@app.post("/analyze")
async def analyze_question(question: str):
    """Analyse une question et montre quelle tool serait utilisée"""
    analysis = analyze_question_type(question)
    
    # Simuler la classification
    try:
        prompt = f"""Question: "{question}"
        
        Catégorise cette question pour un système de garage:
        - DATABASE: questions techniques/requêtes données
        - POLICY: questions sur règles/procédures  
        - SUMMARY: demandes de résumé/synthèse
        - CHAT: conversation générale
        
        Réponds uniquement par le nom de la catégorie."""
        
        classification = call_groq(prompt).strip()
    except:
        classification = "UNKNOWN"
    
    return {
        "question": question,
        "analysis": analysis,
        "recommended_tool": classification,
        "timestamp": time.time()
    }

@app.post("/sql")
async def execute_direct_sql(
    query: str,
    db: Session = Depends(get_db)
):
    """
    Exécute directement une requête SQL
    """
    try:
        df_result = execute_sql_query(query, db)
        
        # Convertir le DataFrame en format lisible
        if df_result.empty:
            result_text = "✅ Requête exécutée. Aucun résultat."
        elif 'message' in df_result.columns:
            result_text = df_result.iloc[0]['message']
        else:
            result_text = df_result.to_string(index=False)
        
        return {
            "query": query,
            "result": result_text,
            "rows_affected": len(df_result),
            "timestamp": time.time()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/{session_id}")
async def get_memory(session_id: str, db: Session = Depends(get_db)):
    """Récupère la mémoire de conversation d'une session depuis la BDD"""
    messages = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).order_by(models.ChatMessage.timestamp).all()
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role, 
                "content": msg.content, 
                "timestamp": msg.timestamp,
                "type": getattr(msg, "type", "text"),
                "imageUrl": getattr(msg, "imageUrl", None)
            } 
            for msg in messages
        ],
        "count": len(messages)
    }

@app.delete("/memory/{session_id}")
async def clear_memory(session_id: str, db: Session = Depends(get_db)):
    """Efface la mémoire d'une session en BDD"""
    chat_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if chat_session:
        db.delete(chat_session)
        db.commit()
        return {"message": f"Mémoire de la session {session_id} effacée"}
    return {"message": f"Session {session_id} non trouvée"}

@app.get("/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """Liste toutes les sessions actives en BDD"""
    sessions = db.query(models.ChatSession).order_by(models.ChatSession.created_at.desc()).all()
    return {
        "sessions": [s.id for s in sessions],
        "count": len(sessions)
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            # Si le message commence par "CMD:", c'est une commande spéciale
            if data.startswith("CMD:"):
                command = data[4:]
                # Traitement commande...
            else:
                # C'est un message de chat, on le traite via l'IA
                try:
                    # On utilise generate_intelligent_response qui gère aussi la sauvegarde en BDD
                    response = generate_intelligent_response(data, client_id, db)
                    await manager.send_personal_message(response, websocket)
                except Exception as e:
                    await manager.send_personal_message(f"❌ Erreur de traitement: {str(e)}", websocket)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Upload une image pour analyse"""
    try:
        # Créer le dossier if not exists
        os.makedirs("uploads", exist_ok=True)
        file_location = f"uploads/{file.filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Analyser avec Vision (Non supporté par modèle text-only actuel)
        description = "Image reçue et stockée."
        # if GROQ_API_KEY:
             # Placeholder pour vision future
             # description = "Analyse image non disponible avec ce modèle."
                
        return {"filename": file.filename, "description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur upload: {str(e)}")

class InvoiceRequest(BaseModel):
    historique_id: int  # ID de l'intervention existante

@app.post("/generate-invoice")
async def generate_invoice(req: InvoiceRequest, db: Session = Depends(get_db)):
    """Génère une facture PDF pour une intervention existante"""
    try:
        # Helper pour éviter les erreurs Unicode
        def sanitize(text):
            if not text:
                return ""
            return str(text).encode('latin-1', 'replace').decode('latin-1')

        # 1. Récupérer l'historique (intervention) existant
        historique = db.query(models.Historique).filter(models.Historique.id == req.historique_id).first()
        if not historique:
            raise HTTPException(status_code=404, detail="Intervention introuvable")

        # 2. Récupérer véhicule et client
        vehicle = db.query(models.Voiture).filter(models.Voiture.matricule == historique.voiture_matricule).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Véhicule introuvable")
            
        client = db.query(models.Client).filter(models.Client.id == vehicle.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client introuvable")

        # 3. Calculer le total
        total = (historique.montant_reparation or 0) + (historique.montant_pieces or 0)

        # 4. Créer la facture en BDD
        invoice_ref = f"FAC-{int(time.time())}"
        new_invoice = models.Facture(
            numero_facture=invoice_ref,
            date_facture=date.today(),
            montant_totale=total,
            resume_reparation=historique.details_reparation or "",
            type_paiement="Espèces",
            client_id=client.id,
            historique_id=historique.id
        )
        db.add(new_invoice)
        db.commit()
        
        # 5. Générer le PDF
        pdf = FPDF()
        pdf.add_page()
        
        # En-tête
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(0, 15, txt=sanitize("GARAGE AUTO"), ln=1, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, txt=sanitize("123 Avenue de la République, Tunis"), ln=1, align="C")
        pdf.cell(0, 5, txt=sanitize("Tél: +216 XX XXX XXX"), ln=1, align="C")
        pdf.ln(10)
        
        # Numéro de facture
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, txt=sanitize(f"FACTURE N° {invoice_ref}"), ln=1, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, txt=sanitize(f"Date: {date.today().strftime('%d/%m/%Y')}"), ln=1, align="C")
        pdf.ln(15)
        
        # Informations Client et Véhicule
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(95, 8, txt="INFORMATIONS CLIENT", border=1, align="C")
        pdf.cell(95, 8, txt="INFORMATIONS VEHICULE", border=1, align="C")
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        # Client
        pdf.cell(95, 6, txt=sanitize(f"  Nom: {client.nom} {client.prenom}"), border=1)
        # Véhicule  
        pdf.cell(95, 6, txt=sanitize(f"  Modèle: {vehicle.modele}"), border=1)
        pdf.ln()
        
        pdf.cell(95, 6, txt=sanitize(f"  Tél: {client.num}"), border=1)
        pdf.cell(95, 6, txt=sanitize(f"  Matricule: {vehicle.matricule}"), border=1)
        pdf.ln()
        
        pdf.cell(95, 6, txt=sanitize(f"  Adresse: {client.adresse or 'N/A'}"), border=1)
        pdf.cell(95, 6, txt=sanitize(f"  Date intervention: {historique.date.strftime('%d/%m/%Y')}"), border=1)
        pdf.ln(15)
        
        # Détails de l'intervention
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, txt="DETAILS DE L'INTERVENTION", border=1, fill=True, align="C")
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, txt=sanitize(historique.details_reparation or "Aucun détail"), border=1)
        pdf.ln(5)
        
        # Tableau des montants
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(140, 8, txt="DESCRIPTION", border=1, fill=True)
        pdf.cell(50, 8, txt="MONTANT (TND)", border=1, fill=True, align="R")
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        pdf.cell(140, 7, txt="  Main d'oeuvre", border=1)
        pdf.cell(50, 7, txt=sanitize(f"{historique.montant_reparation or 0:.2f}"), border=1, align="R")
        pdf.ln()
        
        pdf.cell(140, 7, txt="  Pièces et fournitures", border=1)
        pdf.cell(50, 7, txt=sanitize(f"{historique.montant_pieces or 0:.2f}"), border=1, align="R")
        pdf.ln()
        
        if historique.periode_totale_reparation:
            pdf.cell(140, 7, txt=sanitize(f"  Durée: {historique.periode_totale_reparation} jour(s)"), border=1)
            pdf.cell(50, 7, txt="", border=1)
            pdf.ln()
        
        # Total
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(140, 10, txt="MONTANT TOTAL A PAYER", border=1, fill=True, align="R")
        pdf.cell(50, 10, txt=sanitize(f"{total:.3f} TND"), border=1, fill=True, align="R")
        
        # Pied de page
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(0, 5, txt=sanitize("Merci de votre confiance!"), ln=1, align="C")
        pdf.cell(0, 5, txt=sanitize("Paiement accepté: Espèces, Chèque, Virement"), ln=1, align="C")
        
        # Sauvegarde
        filename = f"facture_{invoice_ref}.pdf"
        filepath = f"public/{filename}"
        os.makedirs("public", exist_ok=True)
        pdf.output(filepath)
        
        return {
            "url": f"/public/{filename}", 
            "total": total,
            "invoice_number": invoice_ref
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Erreur backend: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


@app.get("/tools/info")
async def get_tools_info():
    """Affiche des informations sur les tools disponibles"""
    return {
        "tools": [
            {
                "name": "SmartDatabaseTool",
                "description": "Comprend le langage naturel, génère et exécute du SQL, reformule les résultats",
                "capabilities": [
                    "Conversion langage naturel → SQL",
                    "Exécution de toutes commandes SQL",
                    "Reformulation des résultats en langage naturel",
                    "Analyse contextuelle des questions"
                ]
            },
            {
                "name": "PolicyTool", 
                "description": "Répond aux questions sur les politiques et règles du garage",
                "capabilities": [
                    "Base de connaissances des politiques",
                    "Compréhension des questions procédurales",
                    "Réponses en langage naturel"
                ]
            },
            {
                "name": "SummaryTool",
                "description": "Génère des résumés et synthèses des données",
                "capabilities": [
                    "Agrégation de données",
                    "Génération de rapports",
                    "Synthèse en langage naturel"
                ]
            }
        ]
    }

# ============================================================================
# INCLURE LES ROUTES CRUD
# ============================================================================

try:
    from .routes import (
        clients_router,
        voitures_router,
        historiques_router,
        factures_router,
        pieces_router,
        tarifs_router
    )
    
    app.include_router(clients_router, prefix="/clients", tags=["Clients"])
    app.include_router(voitures_router, prefix="/voitures", tags=["Voitures"])
    app.include_router(historiques_router, prefix="/historiques", tags=["Historiques"])
    app.include_router(factures_router, prefix="/factures", tags=["Factures"])
    app.include_router(pieces_router, prefix="/pieces", tags=["Pièces"])
    app.include_router(tarifs_router, prefix="/tarifs", tags=["Tarifs"])
    
    print("[INFO] Routes CRUD chargees avec succes")
    
except ImportError as e:
    print(f"⚠️ Certaines routes CRUD ne sont pas disponibles: {e}")

# ============================================================================
# ENDPOINT DE DÉMONSTRATION
# ============================================================================

@app.get("/demo")
async def demonstration():
    """Affiche des exemples de ce que le système peut faire"""
    examples = [
        {
            "question": "Combien de clients avons-nous ?",
            "description": "Utilise SmartDatabaseTool pour compter les clients"
        },
        {
            "question": "Quelle est la politique de remise ?",
            "description": "Utilise PolicyTool pour expliquer les règles"
        },
        {
            "question": "Donne-moi un résumé des activités du mois",
            "description": "Utilise SummaryTool pour générer un rapport"
        },
        {
            "question": "Affiche les 5 dernières réparations",
            "description": "Utilise SmartDatabaseTool avec jointures"
        },
        {
            "question": "Crée une nouvelle table de test",
            "description": "Utilise SmartDatabaseTool pour exécuter CREATE TABLE"
        },
        {
            "question": "Quels sont les modes de paiement acceptés ?",
            "description": "Utilise PolicyTool pour les informations procédurales"
        }
    ]
    
    return {
        "system": "Garage Management Intelligent Assistant",
        "version": "2.0.0",
        "examples": examples,
        "try_it": "Utilisez POST /ask avec votre question"
    }