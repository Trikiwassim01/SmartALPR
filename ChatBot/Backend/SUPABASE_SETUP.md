# Configuration Supabase pour le RAG (Google Gemini API)

## 1. Créer la table dans Supabase

Connectez-vous à votre projet Supabase et exécutez le SQL suivant dans l'éditeur SQL.

**⚠️ ATTENTION : La dimension est maintenant de 768 pour supporter le modèle 'models/embedding-001' de Google.**

```sql
-- Activer l'extension pgvector
create extension if not exists vector;

-- Supprimer l'ancienne table si elle existe (ATTENTION : ça efface les données !)
drop table if exists documents;

-- Créer la table documents
create table if not exists documents (
  id bigserial primary key,
  content text not null,
  metadata jsonb,
  embedding vector(768), -- Dimension pour Google Gemini Embedding
  created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Créer un index pour les recherches vectorielles
create index on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Fonction RPC pour la recherche de similarité
create or replace function match_documents (
  query_embedding vector(768),
  match_threshold float default 0.5,
  match_count int default 5
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;
```

## 2. Vérifier les credentials dans .env

Assurez-vous que votre fichier `.env` contient :

```bash
SUPABASE_URL=https://hklmsebmozfaydnhulto.supabase.co
SUPABASE_SERVICE_KEY=
GOOGLE_API_KEY=
```

## 3. Indexer les documents

Placez vos fichiers (PDF, TXT, CSV, Excel, Word, JSON) dans le dossier `uploads/`, puis exécutez :

```bash
python index_documents.py
```

## 4. Tester la recherche

Utilisez le script de test pour vérifier que tout fonctionne :

```bash
python test_rag.py
```
