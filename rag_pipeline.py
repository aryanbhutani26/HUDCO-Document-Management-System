# rag_pipeline.py
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import os

class RAGPipeline:
    def __init__(self, db_connection_string, gemini_api_key):
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Initialize components
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_db = VectorDatabase(db_connection_string)
        
    def process_document(self, pdf_file, filename):
        """Process uploaded document and store in vector DB"""
        processor = DocumentProcessor()
        
        # Extract and chunk text
        text = processor.extract_text_from_pdf(pdf_file)
        chunks = processor.chunk_text(text)
        
        # Create embeddings
        embeddings = processor.create_embeddings(chunks)
        
        # Store in database
        self.vector_db.store_document(filename, chunks, embeddings)
        
        return f"Successfully processed {filename} with {len(chunks)} chunks"
    
    def query_documents(self, user_query):
        """Main RAG query function"""
        # Create query embedding
        query_embedding = self.embedding_model.encode([user_query])[0]
        
        # Retrieve similar chunks
        similar_chunks = self.vector_db.retrieve_similar_chunks(query_embedding, limit=5)
        
        # Prepare context from retrieved chunks
        context = "\n\n".join([chunk for chunk in similar_chunks])
        
        # Create secure prompt with strict grounding
        prompt = self.create_grounded_prompt(user_query, context)
        
        # Generate response using Gemini
        response = self.model.generate_content(prompt)
        
        return {
            'answer': response.text,
            'sources': [{'filename': chunk[11], 'similarity': chunk[12]} for chunk in similar_chunks]
        }
    
    def create_grounded_prompt(self, query, context):
        """Create a secure prompt that prevents hallucination"""
        return f"""
        You are a document assistant. Answer the question based ONLY on the provided context.
        
        STRICT RULES:
        1. Only use information from the provided context below
        2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in the provided documents to answer this question."
        3. Do not make assumptions or add information not present in the context
        4. Always cite which part of the context you're using
        
        CONTEXT:
        {context}
        
        QUESTION: {query}
        
        ANSWER (based only on the context above):
        """
