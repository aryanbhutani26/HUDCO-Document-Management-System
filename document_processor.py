# document_processor.py
import PyPDF2
import io
from sentence_transformers import SentenceTransformer
import numpy as np

class DocumentProcessor:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from uploaded PDF"""
        text = ""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
        
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    
    def chunk_text(self, text, chunk_size=500, overlap=50):
        """Split text into chunks for better retrieval"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def create_embeddings(self, text_chunks):
        """Generate embeddings for text chunks"""
        embeddings = self.embedding_model.encode(text_chunks)
        return embeddings
