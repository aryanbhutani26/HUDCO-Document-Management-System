# database.py
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector

class VectorDatabase:
    def __init__(self, connection_string):
        self.conn = psycopg2.connect(connection_string)
        register_vector(self.conn)
        self.setup_database()
    
    def setup_database(self):
        """Create tables for storing documents and embeddings"""
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255),
                    chunk_text TEXT,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops)")
        self.conn.commit()
    
    def store_document(self, filename, chunks, embeddings):
        """Store document chunks and their embeddings"""
        with self.conn.cursor() as cur:
            for chunk, embedding in zip(chunks, embeddings):
                cur.execute(
                    "INSERT INTO documents (filename, chunk_text, embedding) VALUES (%s, %s, %s)",
                    (filename, chunk, embedding.tolist())
                )
        self.conn.commit()
    
    def retrieve_similar_chunks(self, query_embedding, limit=5):
        """Retrieve most similar document chunks"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_text, filename, 1 - (embedding <=> %s) as similarity
                FROM documents
                ORDER BY embedding <=> %s
                LIMIT %s
            """, (query_embedding.tolist(), query_embedding.tolist(), limit))
            
            results = cur.fetchall()
            return results
