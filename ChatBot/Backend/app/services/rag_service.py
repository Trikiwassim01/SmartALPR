import os
from pathlib import Path
from typing import List, Any, Dict
import asyncio
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, CSVLoader, Docx2txtLoader, JSONLoader
)
from langchain_community.document_loaders.excel import UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client, Client
import google.generativeai as genai

load_dotenv()

class RAGService:
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Google AI Config
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            print("[ERROR] GOOGLE_API_KEY not found.")
            
        genai.configure(api_key=self.google_api_key)
        
        # Initialize Embeddings model
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=self.google_api_key
        )
        
        # Supabase Config
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            print("[WARNING] Supabase credentials not found in environment variables.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            print(f"[INFO] Connected to Supabase: {self.supabase_url}")
            
    def load_all_documents(self, data_dir: str) -> List[Any]:
        """
        Load all supported files from the data directory and convert to LangChain document structure.
        """
        data_path = Path(data_dir).resolve()
        if not data_path.exists():
            print(f"[ERROR] Data path does not exist: {data_path}")
            return []
            
        print(f"[DEBUG] Data path: {data_path}")
        documents = []

        loaders = {
            "**/*.pdf": PyPDFLoader,
            # "**/*.txt": TextLoader, # Encoding issues often happen with TextLoader, handle with care or custom one
            "**/*.csv": CSVLoader,
            # "**/*.xlsx": UnstructuredExcelLoader, # Requires extra dependencies
            # "**/*.docx": Docx2txtLoader,
            # "**/*.docx": Docx2txtLoader,
            "**/*.json": JSONLoader,
            "**/*.md": TextLoader
        }

        # Handle TXT and MD specifically for utf-8
        text_files = list(data_path.glob("**/*.txt")) + list(data_path.glob("**/*.md"))
        for f in text_files:
            try:
                loader = TextLoader(str(f), encoding='utf-8')
                documents.extend(loader.load())
                print(f"[DEBUG] Loaded {f.name}")
            except Exception as e:
                print(f"[ERROR] Failed Text/MD {f.name}: {e}")

        for pattern, loader_class in loaders.items():
            if pattern == "**/*.md": continue # handled above
            files = list(data_path.glob(pattern))
            for file in files:
                try:
                    loader = loader_class(str(file))
                    loaded = loader.load()
                    documents.extend(loaded)
                    print(f"[DEBUG] Loaded {len(loaded)} docs from {file.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to load {file.name}: {e}")

        print(f"[DEBUG] Total loaded documents: {len(documents)}")
        return documents

    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        print(f"[INFO] Split {len(documents)} documents into {len(chunks)} chunks.")
        return chunks

    def embed_chunks(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        texts = [chunk.page_content for chunk in chunks]
        print(f"[INFO] Generating embeddings for {len(texts)} chunks via Google API...")
        
        # Batching because API might have limits
        batch_size = 10
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            try:
                # Use langchain wrapper to embed documents
                batch_embeddings = self.embeddings.embed_documents(batch_texts)
                all_embeddings.extend(batch_embeddings)
                print(f"   Processed batch {i}-{i+len(batch_texts)}")
            except Exception as e:
                print(f"[ERROR] Embedding batch failed: {e}")
                # Add placeholders or retry logic could go here
        
        result = []
        # Only zip what we successfully embedded
        for i, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            result.append({
                "id": f"chunk_{i}",
                "content": chunk.page_content,
                "metadata": chunk.metadata,
                "embedding": embedding 
            })
        return result

    async def store_in_supabase(self, embedded_chunks: List[Dict[str, Any]]):
        """
        Store embedded chunks in Supabase vector table.
        """
        if not self.supabase:
            print("[ERROR] Cannot store in Supabase: Client not initialized.")
            return

        print(f"[INFO] Storing {len(embedded_chunks)} chunks in Supabase...")
        
        # Insert in batches
        batch_size = 50
        for i in range(0, len(embedded_chunks), batch_size):
            batch = embedded_chunks[i:i+batch_size]
            data = [
                {
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "embedding": item["embedding"]
                }
                for item in batch
            ]
            try:
                self.supabase.table("documents").insert(data).execute()
            except Exception as e:
                print(f"[ERROR] Batch insertion failed: {e}")

    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents in Supabase using the query embedding.
        """
        if not self.supabase:
            return []

        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            response = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.3, # Abaissé pour plus de résultats
                    "match_count": limit
                }
            ).execute()
            return response.data
        except Exception as e:
            print(f"[ERROR] Similarity search failed: {e}")
            return []
