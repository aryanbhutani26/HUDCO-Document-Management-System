
# # Flask Backend version 4 - RAG Integration (Error-Free)

# import os
# import uuid
# import hashlib
# import logging
# import shutil
# import subprocess
# import io
# import re
# import html
# from pathlib import Path
# from flask import Flask, request, jsonify, render_template
# import psycopg2
# from werkzeug.utils import secure_filename
# from psycopg2.extras import Json
# from dotenv import load_dotenv
# from flask_cors import CORS

# # RAG-specific imports
# import google.generativeai as genai
# from sentence_transformers import SentenceTransformer
# import PyPDF2
# import numpy as np
# from pgvector.psycopg2 import register_vector

# load_dotenv()

# # Config
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_NAME = os.getenv("DB_NAME", "pdf_dms")
# DB_USER = os.getenv("DB_USER", "dms_user")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "aryan")
# CLAMSCAN_PATH = os.getenv("CLAMSCAN_PATH", r"C:\Program Files\ClamAV\clamscan.exe")
# FRESHCLAM_PATH = os.getenv("FRESHCLAM_PATH", r"C:\Program Files\ClamAV\freshclam.exe")
# CLAMAV_DB_DIR = os.getenv("CLAMAV_DB_DIR", r"C:\Program Files\ClamAV\database")
# MAX_FILE_BYTES = int(os.getenv("MAX_FILE_SIZE", str(200 * 1024 * 1024)))
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAKFNYPNWvZ1lefBXWYXzSbIBGjzqPD1DM")
# ROOT_DIR = Path(__file__).resolve().parent
# UPLOAD_DIR = ROOT_DIR / "pdf-questions-dms" / "uploads"
# QUARANTINE_DIR = ROOT_DIR / "pdf-questions-dms" / "quarantine"
# CLEAN_DIR = ROOT_DIR / "pdf-questions-dms" / "clean_uploads"
# TEMP_DIR = ROOT_DIR / "temp"
# LOG_DIR = ROOT_DIR / "logs"

# ALLOWED_EXTENSIONS = {".pdf"}
# ALLOWED_MIMES = {"application/pdf"}

# # Logging
# LOG_DIR.mkdir(exist_ok=True, parents=True)
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(message)s",
#     handlers=[
#         logging.FileHandler(LOG_DIR / "security.log", encoding="utf-8"),
#         logging.StreamHandler()
#     ],
# )
# logger = logging.getLogger("dms")

# # Global variable to track RAG initialization
# rag_pipeline = None
# rag_initialized = False

# # RAG Classes and Functions
# class SecurityManager:
#     @staticmethod
#     def sanitize_input(text):
#         """Sanitize user input to prevent prompt injection"""
#         if not text:
#             return ""
        
#         # Remove HTML tags
#         text = html.escape(str(text))
        
#         # Remove potential instruction keywords
#         dangerous_patterns = [
#             r'ignore\s+previous\s+instructions',
#             r'system\s*:',
#             r'assistant\s*:',
#             r'<\s*/?system\s*>',
#             r'<\s*/?assistant\s*>',
#             r'pretend\s+to\s+be',
#             r'act\s+as\s+if',
#             r'roleplay\s+as'
#         ]
        
#         for pattern in dangerous_patterns:
#             text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
#         return text.strip()

# class DocumentProcessor:
#     def __init__(self):
#         try:
#             self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
#             logger.info("Document processor initialized successfully")
#         except Exception as e:
#             logger.error(f"Failed to initialize document processor: {e}")
#             raise e
    
#     def extract_text_from_pdf(self, file_path):
#         """Extract text from PDF file"""
#         text = ""
#         try:
#             with open(file_path, 'rb') as file:
#                 pdf_reader = PyPDF2.PdfReader(file)
#                 for page_num, page in enumerate(pdf_reader.pages):
#                     try:
#                         page_text = page.extract_text()
#                         if page_text:
#                             text += page_text + "\n"
#                     except Exception as e:
#                         logger.warning(f"Failed to extract text from page {page_num}: {e}")
#                         continue
                        
#             if not text.strip():
#                 raise ValueError("No readable text found in PDF")
                
#         except Exception as e:
#             logger.error(f"PDF text extraction failed: {e}")
#             raise e
#         return text
    
#     def chunk_text(self, text, chunk_size=500, overlap=50):
#         """Split text into chunks for better retrieval"""
#         if not text or not text.strip():
#             return []
            
#         words = text.split()
#         if len(words) == 0:
#             return []
            
#         chunks = []
        
#         for i in range(0, len(words), chunk_size - overlap):
#             chunk = ' '.join(words[i:i + chunk_size])
#             if chunk.strip():  # Only add non-empty chunks
#                 chunks.append(chunk.strip())
        
#         return chunks
    
#     def create_embeddings(self, text_chunks):
#         """Generate embeddings for text chunks"""
#         if not text_chunks:
#             return np.array([])
            
#         try:
#             embeddings = self.embedding_model.encode(text_chunks)
#             return embeddings
#         except Exception as e:
#             logger.error(f"Failed to create embeddings: {e}")
#             raise e

# class VectorDatabase:
#     def __init__(self):
#         self.connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
#         self.db_ready = False
        
#     def get_connection(self):
#         try:
#             conn = psycopg2.connect(self.connection_string)
#             register_vector(conn)
#             return conn
#         except Exception as e:
#             logger.error(f"Failed to connect to database: {e}")
#             raise e
    
#     def setup_database(self):
#         """Create tables for storing document chunks and embeddings"""
#         try:
#             with self.get_connection() as conn:
#                 with conn.cursor() as cur:
#                     # Check if pgvector extension exists
#                     cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    
#                     # Create document_chunks table
#                     cur.execute("""
#                         CREATE TABLE IF NOT EXISTS document_chunks (
#                             id SERIAL PRIMARY KEY,
#                             document_id VARCHAR(255),
#                             chunk_index INTEGER,
#                             chunk_text TEXT,
#                             embedding vector(384),
#                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                         )
#                     """)
                    
#                     # Create index for better performance (only if table is new or index doesn't exist)
#                     cur.execute("""
#                         DO $$
#                         BEGIN
#                             IF NOT EXISTS (
#                                 SELECT 1 FROM pg_indexes 
#                                 WHERE indexname = 'chunk_embedding_idx'
#                             ) THEN
#                                 CREATE INDEX chunk_embedding_idx 
#                                 ON document_chunks USING ivfflat (embedding vector_cosine_ops)
#                                 WITH (lists = 100);
#                             END IF;
#                         END
#                         $$;
#                     """)
                    
#                     # Add foreign key constraint if documents table exists
#                     cur.execute("""
#                         DO $$ 
#                         BEGIN
#                             IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
#                                 IF NOT EXISTS (
#                                     SELECT 1 FROM information_schema.table_constraints 
#                                     WHERE constraint_name = 'fk_document_id'
#                                 ) THEN
#                                     ALTER TABLE document_chunks 
#                                     ADD CONSTRAINT fk_document_id 
#                                     FOREIGN KEY (document_id) REFERENCES documents(id)
#                                     ON DELETE CASCADE;
#                                 END IF;
#                             END IF;
#                         EXCEPTION
#                             WHEN duplicate_object THEN NULL;
#                         END $$;
#                     """)
                    
#                 conn.commit()
#                 self.db_ready = True
#                 logger.info("Database setup completed successfully")
                
#         except psycopg2.errors.InsufficientPrivilege as e:
#             logger.error(f"Database permission error: {e}")
#             logger.error("Please run the following SQL commands as a superuser:")
#             logger.error("GRANT CREATE ON SCHEMA public TO dms_user;")
#             logger.error("GRANT USAGE ON SCHEMA public TO dms_user;")
#             raise e
#         except Exception as e:
#             logger.error(f"Database setup failed: {e}")
#             raise e
    
#     def ensure_tables_exist(self):
#         """Check if tables exist, create if they don't"""
#         try:
#             with self.get_connection() as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("""
#                         SELECT EXISTS (
#                             SELECT 1 FROM information_schema.tables 
#                             WHERE table_name = 'document_chunks'
#                         )
#                     """)
#                     table_exists = cur.fetchone()[0]
                    
#                     if not table_exists:
#                         logger.warning("document_chunks table doesn't exist, attempting to create...")
#                         self.setup_database()
#                     else:
#                         self.db_ready = True
                    
#                     return True
#         except Exception as e:
#             logger.error(f"Failed to ensure tables exist: {e}")
#             return False
    
#     def store_document_chunks(self, document_id, chunks, embeddings):
#         """Store document chunks and their embeddings"""
#         if not self.db_ready:
#             if not self.ensure_tables_exist():
#                 raise RuntimeError("Database not ready for storing chunks")
                
#         try:
#             with self.get_connection() as conn:
#                 with conn.cursor() as cur:
#                     # First, delete any existing chunks for this document
#                     cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
                    
#                     # Insert new chunks
#                     for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
#                         cur.execute("""
#                             INSERT INTO document_chunks (document_id, chunk_index, chunk_text, embedding)
#                             VALUES (%s, %s, %s, %s)
#                         """, (document_id, i, chunk, embedding.tolist()))
#                 conn.commit()
#                 logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
                
#         except Exception as e:
#             logger.error(f"Failed to store chunks: {e}")
#             raise e
    
#     def retrieve_similar_chunks(self, query_embedding, limit=5, document_id=None):
#         """Retrieve most similar document chunks"""
#         if not self.db_ready:
#             if not self.ensure_tables_exist():
#                 raise RuntimeError("Database not ready for retrieving chunks")
                
#         try:
#             with self.get_connection() as conn:
#                 with conn.cursor() as cur:
#                     if document_id:
#                         cur.execute("""
#                             SELECT dc.chunk_text, d.original_filename, 1 - (dc.embedding <=> %s) as similarity
#                             FROM document_chunks dc
#                             JOIN documents d ON dc.document_id = d.id
#                             WHERE dc.document_id = %s
#                             ORDER BY dc.embedding <=> %s
#                             LIMIT %s
#                         """, (query_embedding.tolist(), document_id, query_embedding.tolist(), limit))
#                     else:
#                         cur.execute("""
#                             SELECT dc.chunk_text, d.original_filename, 1 - (dc.embedding <=> %s) as similarity
#                             FROM document_chunks dc
#                             JOIN documents d ON dc.document_id = d.id
#                             WHERE d.scan_status = 'clean' AND d.is_processed = true
#                             ORDER BY dc.embedding <=> %s
#                             LIMIT %s
#                         """, (query_embedding.tolist(), query_embedding.tolist(), limit))
                    
#                     results = cur.fetchall()
#                     return results
#         except Exception as e:
#             logger.error(f"Failed to retrieve chunks: {e}")
#             raise e

# class RAGPipeline:
#     def __init__(self):
#         try:
#             # Initialize Gemini
#             genai.configure(api_key=GEMINI_API_KEY)
#             self.model = genai.GenerativeModel('gemini-pro')
            
#             # Initialize components
#             self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
#             self.vector_db = VectorDatabase()
#             self.document_processor = DocumentProcessor()
#             self.security_manager = SecurityManager()
            
#             logger.info("RAG pipeline initialized successfully")
            
#         except Exception as e:
#             logger.error(f"Failed to initialize RAG pipeline: {e}")
#             raise e
        
#     def process_document_for_rag(self, document_id, file_path):
#         """Process a clean document and store embeddings"""
#         try:
#             # Ensure database is ready
#             if not self.vector_db.ensure_tables_exist():
#                 raise RuntimeError("Database not ready for RAG processing")
            
#             # Extract text from PDF
#             text = self.document_processor.extract_text_from_pdf(file_path)
            
#             if not text.strip():
#                 raise ValueError("No text content found in PDF")
            
#             # Chunk the text
#             chunks = self.document_processor.chunk_text(text)
            
#             if not chunks:
#                 raise ValueError("No valid chunks created from text")
            
#             # Create embeddings
#             embeddings = self.document_processor.create_embeddings(chunks)
            
#             if embeddings.size == 0:
#                 raise ValueError("Failed to create embeddings")
            
#             # Store in vector database
#             self.vector_db.store_document_chunks(document_id, chunks, embeddings)
            
#             # Update document as processed
#             with db_connect() as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("""
#                         UPDATE documents SET is_processed = true, processed_at = CURRENT_TIMESTAMP
#                         WHERE id = %s
#                     """, (document_id,))
#                 conn.commit()
            
#             logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
#             return len(chunks)
            
#         except Exception as e:
#             logger.error(f"RAG processing failed for {document_id}: {e}")
#             raise e
    
#     def query_documents(self, user_query, document_id=None):
#         """Main RAG query function"""
#         try:
#             # Ensure database is ready
#             if not self.vector_db.ensure_tables_exist():
#                 raise RuntimeError("Database not ready for querying")
            
#             # Sanitize input
#             sanitized_query = self.security_manager.sanitize_input(user_query)
            
#             if len(sanitized_query.strip()) < 3:
#                 raise ValueError("Query too short after sanitization")
            
#             # Create query embedding
#             query_embedding = self.embedding_model.encode([sanitized_query])[0]
            
#             # Retrieve similar chunks
#             similar_chunks = self.vector_db.retrieve_similar_chunks(
#                 query_embedding, limit=5, document_id=document_id
#             )
            
#             if not similar_chunks:
#                 return {
#                     'answer': "No relevant information found in the documents.",
#                     'sources': [],
#                     'query': sanitized_query
#                 }
            
#             # Prepare context from retrieved chunks
#             context = "\n\n".join([f"Source: {chunk[1]}\nContent: {chunk[0]}" for chunk in similar_chunks])
            
#             # Create secure prompt with strict grounding
#             prompt = self.create_grounded_prompt(sanitized_query, context)
            
#             # Generate response using Gemini
#             response = self.model.generate_content(prompt)
            
#             return {
#                 'answer': response.text,
#                 'sources': [{'filename': chunk[1], 'similarity': round(chunk[1], 3)} for chunk in similar_chunks],
#                 'query': sanitized_query
#             }
            
#         except Exception as e:
#             logger.error(f"Query processing failed: {e}")
#             raise e
    
#     def create_grounded_prompt(self, query, context):
#         """Create a secure prompt that prevents hallucination"""
#         return f"""
#         You are a document assistant. Answer the question based ONLY on the provided context.
        
#         STRICT RULES:
#         1. Only use information from the provided context below
#         2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in the provided documents to answer this question."
#         3. Do not make assumptions or add information not present in the context
#         4. Always be factual and cite which source you're referencing
#         5. Keep responses concise and relevant
        
#         CONTEXT:
#         {context}
        
#         QUESTION: {query}
        
#         ANSWER (based only on the context above):
#         """

# # Initialize RAG Pipeline with error handling
# def initialize_rag_pipeline():
#     """Initialize RAG pipeline with proper error handling"""
#     global rag_pipeline, rag_initialized
    
#     try:
#         if not rag_initialized:
#             logger.info("Initializing RAG pipeline...")
#             rag_pipeline = RAGPipeline()
#             rag_initialized = True
#             logger.info("RAG pipeline initialized successfully")
#     except Exception as e:
#         logger.error(f"Failed to initialize RAG pipeline: {e}")
#         rag_pipeline = None
#         rag_initialized = False

# # Existing helper functions (unchanged)
# def db_connect():
#     try:
#         return psycopg2.connect(
#             host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
#         )
#     except Exception as e:
#         logger.error(f"Database connection failed: {e}")
#         raise e

# def init_dirs():
#     for d in (UPLOAD_DIR, QUARANTINE_DIR, CLEAN_DIR, TEMP_DIR, LOG_DIR):
#         d.mkdir(exist_ok=True, parents=True)

# def get_file_hash(file_path: Path) -> str:
#     h = hashlib.sha256()
#     with open(file_path, "rb") as f:
#         for chunk in iter(lambda: f.read(1 << 20), b""):
#             h.update(chunk)
#     return h.hexdigest()

# def extension_allowed(filename: str) -> bool:
#     return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

# def file_magic_mime(file_path: Path) -> str:
#     try:
#         import magic
#         m = magic.Magic(mime=True)
#         return m.from_file(str(file_path))
#     except Exception as e:
#         logger.warning(f"MIME detection failed or library unavailable: {e}")
#         return ""

# def log_security_event(event_type: str, details, document_id=None, user_id=None, ip_address=None):
#     try:
#         details_obj = details if isinstance(details, (dict, list)) else {"message": str(details)}
#         with db_connect() as conn, conn.cursor() as cur:
#             cur.execute("""
#                 INSERT INTO audit_logs (event_type, document_id, user_id, details, ip_address)
#                 VALUES (%s, %s, %s, %s, %s)
#             """, (event_type, document_id, user_id, Json(details_obj), ip_address))
#             conn.commit()
#     except Exception as e:
#         logger.error(f"Failed to log security event: {e} | {event_type} | {details}")

# def clamav_db_present() -> bool:
#     db_dir = Path(CLAMAV_DB_DIR)
#     return db_dir.exists() and any(db_dir.iterdir())

# def try_freshclam_once() -> tuple:
#     try:
#         if not Path(FRESHCLAM_PATH).exists():
#             return False, "freshclam.exe not found"
#         result = subprocess.run(
#             [FRESHCLAM_PATH],
#             capture_output=True,
#             text=True,
#             timeout=180,
#             shell=False
#         )
#         ok = result.returncode == 0
#         msg = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
#         return ok, msg.strip()
#     except subprocess.TimeoutExpired:
#         return False, "freshclam timed out"
#     except Exception as e:
#         return False, f"freshclam error: {e}"

# def parse_clamscan_output(stdout: str, returncode: int) -> tuple:
#     out = (stdout or "").strip()
#     if "FOUND" in out:
#         return (False, out)
#     if returncode == 0:
#         return (True, "Clean")
#     if returncode == 1:
#         return (False, out or "Virus found")
#     return (False, out or f"Scan failed with code {returncode}")

# def scan_with_clamscan(file_path: Path) -> tuple:
#     if not Path(CLAMSCAN_PATH).exists():
#         return False, f"clamscan.exe not found at {CLAMSCAN_PATH}"
#     if not clamav_db_present():
#         return False, f"ClamAV database missing at {CLAMAV_DB_DIR}. Run freshclam once."
#     try:
#         result = subprocess.run(
#             [CLAMSCAN_PATH, "--no-summary", str(file_path)],
#             capture_output=True,
#             text=True,
#             timeout=300,
#             shell=False
#         )
#         stdout = result.stdout
#         stderr = result.stderr.strip()
#         is_clean, msg = parse_clamscan_output(stdout, result.returncode)
#         if not is_clean and not msg:
#             msg = stderr or "Unknown scan error"
#         return is_clean, msg
#     except subprocess.TimeoutExpired:
#         return False, "Scan timeout"
#     except Exception as e:
#         return False, f"Scan error: {e}"

# # Flask App
# app = Flask(__name__)
# CORS(app)
# app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES

# appHasRunBefore = False

# @app.before_request
# def setup():
#     global appHasRunBefore
#     if not appHasRunBefore:
#         init_dirs()
#         logger.info("Directories ensured.")
#         if not clamav_db_present():
#             ok, msg = try_freshclam_once()
#             logger.info(f"freshclam attempted on startup: ok={ok} msg={(msg or '')[:400]}")
        
#         # Initialize RAG pipeline
#         initialize_rag_pipeline()
#         appHasRunBefore = True

# @app.route("/health", methods=["GET"])
# def health():
#     status = "ok" if Path(CLAMSCAN_PATH).exists() else "clamscan_not_found"
#     db_ok = clamav_db_present()
#     return jsonify({
#         "status": status,
#         "clamav_db_present": db_ok,
#         "upload_dir": str(UPLOAD_DIR),
#         "quarantine_dir": str(QUARANTINE_DIR),
#         "clean_dir": str(CLEAN_DIR),
#         "rag_enabled": rag_initialized,
#         "rag_status": "initialized" if rag_initialized else "failed"
#     }), 200

# # Existing upload route (unchanged)
# @app.route("/upload", methods=["POST"])
# def upload_file():
#     client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
#     user_id = request.headers.get("X-User-ID", "anonymous")
#     try:
#         if "file" not in request.files:
#             log_security_event("UPLOAD_REJECTED", {"reason": "No file provided"}, user_id=user_id, ip_address=client_ip)
#             return jsonify({"error": "No file provided"}), 400
#         file = request.files["file"]
#         if not file or file.filename == "":
#             return jsonify({"error": "No file selected"}), 400
#         original_filename = file.filename
#         file_ext = Path(original_filename).suffix.lower()
#         if file_ext not in ALLOWED_EXTENSIONS:
#             log_security_event("UPLOAD_REJECTED", {"reason": "Invalid extension", "filename": original_filename}, user_id=user_id, ip_address=client_ip)
#             return jsonify({"error": "Only PDF files are allowed"}), 400
#         # Save to quarantine first with UUID name
#         doc_id = str(uuid.uuid4())
#         quarantine_path = QUARANTINE_DIR / f"{doc_id}.pdf"
#         file.save(quarantine_path)
#         # Size check (defense-in-depth)
#         if quarantine_path.stat().st_size > MAX_FILE_BYTES:
#             quarantine_path.unlink(missing_ok=True)
#             log_security_event("UPLOAD_REJECTED", {"reason": "Too large", "limit": MAX_FILE_BYTES}, user_id=user_id, ip_address=client_ip)
#             return jsonify({"error": "File too large"}), 413
#         # MIME best-effort check
#         detected_mime = file_magic_mime(quarantine_path)
#         if detected_mime and detected_mime not in ALLOWED_MIMES:
#             quarantine_path.unlink(missing_ok=True)
#             log_security_event("UPLOAD_REJECTED", {"reason": "MIME mismatch", "mime": detected_mime, "filename": original_filename}, user_id=user_id, ip_address=client_ip)
#             return jsonify({"error": "File is not a valid PDF"}), 400
#         file_hash = get_file_hash(quarantine_path)
#         file_size = quarantine_path.stat().st_size
#         # Insert DB record as pending
#         with db_connect() as conn, conn.cursor() as cur:
#             cur.execute("""
#                 INSERT INTO documents (id, original_filename, file_path, file_hash, file_size, owner_id, scan_status)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#             """, (doc_id, original_filename, str(quarantine_path), file_hash, file_size, user_id, "pending"))
#             conn.commit()
#         log_security_event("FILE_UPLOADED", {"filename": original_filename, "size": file_size}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
#         # Synchronous scan
#         is_clean, scan_msg = scan_with_clamscan(quarantine_path)
#         with db_connect() as conn, conn.cursor() as cur:
#             if is_clean:
#                 # Move to clean directory
#                 clean_path = CLEAN_DIR / quarantine_path.name
#                 CLEAN_DIR.mkdir(exist_ok=True, parents=True)
#                 shutil.move(str(quarantine_path), str(clean_path))
#                 cur.execute("""
#                     UPDATE documents
#                     SET scan_status=%s, scan_result=%s, file_path=%s
#                     WHERE id=%s
#                 """, ("clean", scan_msg, str(clean_path), doc_id))
#                 conn.commit()
#                 log_security_event("FILE_SCAN_CLEAN", {"result": scan_msg}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
#                 return jsonify({"document_id": doc_id, "status": "clean", "message": "File scanned clean and ready for processing"}), 200
#             else:
#                 # Keep in quarantine; mark infected or error
#                 cur.execute("""
#                     UPDATE documents
#                     SET scan_status=%s, scan_result=%s
#                     WHERE id=%s
#                 """, ("infected", scan_msg, doc_id))
#                 conn.commit()
#                 log_security_event("FILE_SCAN_INFECTED", {"result": scan_msg}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
#                 hint = "Virus DB missing. Run freshclam once (as Admin) in C:\\Program Files\\ClamAV." if "database missing" in scan_msg.lower() else None
#                 return jsonify({
#                     "document_id": doc_id,
#                     "status": "infected",
#                     "error": "File failed antivirus scan",
#                     "details": scan_msg,
#                     "hint": hint
#                 }), 400
#     except Exception as e:
#         logger.exception("Upload error")
#         log_security_event("UPLOAD_ERROR", {"error": str(e)}, user_id=user_id, ip_address=client_ip)
#         return jsonify({"error": "Upload failed"}), 500

# # NEW RAG ROUTES

# @app.route("/setup-database", methods=["POST"])
# def setup_database():
#     """Manually trigger database setup"""
#     if not rag_initialized:
#         return jsonify({
#             "error": "RAG system not initialized",
#             "message": "Please restart the application"
#         }), 503
    
#     try:
#         rag_pipeline.vector_db.setup_database()
#         return jsonify({"message": "Database setup completed successfully"}), 200
#     except Exception as e:
#         return jsonify({
#             "error": "Database setup failed", 
#             "details": str(e),
#             "solution": "Please grant CREATE permissions to dms_user: GRANT CREATE ON SCHEMA public TO dms_user;"
#         }), 500

# @app.route("/process-document/<doc_id>", methods=["POST"])
# def process_document_for_rag(doc_id):
#     """Process a clean document for RAG functionality"""
#     if not rag_initialized:
#         return jsonify({
#             "error": "RAG system not available",
#             "message": "RAG pipeline failed to initialize. Check logs for details."
#         }), 503
    
#     client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
#     user_id = request.headers.get("X-User-ID", "anonymous")
    
#     try:
#         # Check if document exists and is clean
#         with db_connect() as conn:
#             with conn.cursor() as cur:
#                 cur.execute("""
#                     SELECT scan_status, file_path, is_processed, original_filename
#                     FROM documents WHERE id = %s
#                 """, (doc_id,))
#                 row = cur.fetchone()
        
#         if not row:
#             return jsonify({"error": "Document not found"}), 404
        
#         scan_status, file_path, is_processed, original_filename = row
        
#         if scan_status != "clean":
#             return jsonify({"error": "Document must be scanned clean before processing"}), 400
        
#         if is_processed:
#             return jsonify({"message": "Document already processed for RAG"}), 200
        
#         # Process document with RAG pipeline
#         chunk_count = rag_pipeline.process_document_for_rag(doc_id, file_path)
        
#         log_security_event("DOCUMENT_PROCESSED_RAG", {
#             "filename": original_filename,
#             "chunk_count": chunk_count
#         }, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        
#         return jsonify({
#             "message": f"Document processed successfully for RAG with {chunk_count} chunks",
#             "document_id": doc_id,
#             "chunk_count": chunk_count
#         }), 200
        
#     except Exception as e:
#         logger.error(f"RAG processing error for {doc_id}: {e}")
#         log_security_event("DOCUMENT_PROCESSING_ERROR", {
#             "error": str(e)
#         }, document_id=doc_id, user_id=user_id, ip_address=client_ip)
#         return jsonify({"error": "Document processing failed", "details": str(e)}), 500

# @app.route("/query", methods=["POST"])
# def query_documents():
#     """Query all processed documents using RAG"""
#     if not rag_initialized:
#         return jsonify({
#             "error": "RAG system not available",
#             "message": "RAG pipeline failed to initialize. Check logs for details."
#         }), 503
    
#     client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
#     user_id = request.headers.get("X-User-ID", "anonymous")
    
#     try:
#         data = request.get_json()
        
#         if not data or 'query' not in data:
#             return jsonify({'error': 'Query is required'}), 400
        
#         user_query = data['query'].strip()
        
#         # Input validation
#         if len(user_query) > 500:
#             return jsonify({'error': 'Query too long (max 500 characters)'}), 400
        
#         if len(user_query) < 3:
#             return jsonify({'error': 'Query too short (min 3 characters)'}), 400
        
#         # Process query with RAG pipeline
#         result = rag_pipeline.query_documents(user_query)
        
#         log_security_event("DOCUMENT_QUERY", {
#             "original_query": user_query,
#             "sanitized_query": result.get('query', ''),
#             "sources_count": len(result.get('sources', []))
#         }, user_id=user_id, ip_address=client_ip)
        
#         return jsonify(result), 200
        
#     except Exception as e:
#         logger.error(f"Query error: {e}")
#         log_security_event("QUERY_ERROR", {"error": str(e)}, user_id=user_id, ip_address=client_ip)
#         return jsonify({"error": "Query processing failed", "details": str(e)}), 500

# @app.route("/query-document/<doc_id>", methods=["POST"])
# def query_specific_document(doc_id):
#     """Query a specific document using RAG"""
#     if not rag_initialized:
#         return jsonify({
#             "error": "RAG system not available",
#             "message": "RAG pipeline failed to initialize. Check logs for details."
#         }), 503
    
#     client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
#     user_id = request.headers.get("X-User-ID", "anonymous")
    
#     try:
#         # Check if document exists and is processed
#         with db_connect() as conn:
#             with conn.cursor() as cur:
#                 cur.execute("""
#                     SELECT scan_status, is_processed, original_filename
#                     FROM documents WHERE id = %s
#                 """, (doc_id,))
#                 row = cur.fetchone()
        
#         if not row:
#             return jsonify({"error": "Document not found"}), 404
        
#         scan_status, is_processed, original_filename = row
        
#         if scan_status != "clean" or not is_processed:
#             return jsonify({"error": "Document must be processed for RAG before querying"}), 400
        
#         data = request.get_json()
        
#         if not data or 'query' not in data:
#             return jsonify({'error': 'Query is required'}), 400
        
#         user_query = data['query'].strip()
        
#         # Input validation
#         if len(user_query) > 500:
#             return jsonify({'error': 'Query too long (max 500 characters)'}), 400
        
#         if len(user_query) < 3:
#             return jsonify({'error': 'Query too short (min 3 characters)'}), 400
        
#         # Process query with RAG pipeline for specific document
#         result = rag_pipeline.query_documents(user_query, document_id=doc_id)
        
#         log_security_event("SPECIFIC_DOCUMENT_QUERY", {
#             "filename": original_filename,
#             "original_query": user_query,
#             "sanitized_query": result.get('query', ''),
#             "sources_count": len(result.get('sources', []))
#         }, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        
#         return jsonify(result), 200
        
#     except Exception as e:
#         logger.error(f"Specific document query error: {e}")
#         log_security_event("SPECIFIC_QUERY_ERROR", {"error": str(e)}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
#         return jsonify({"error": "Query processing failed", "details": str(e)}), 500

# @app.route("/documents", methods=["GET"])
# def list_documents():
#     """List all processed documents available for querying"""
#     try:
#         with db_connect() as conn:
#             with conn.cursor() as cur:
#                 cur.execute("""
#                     SELECT id, original_filename, file_size, scan_status, is_processed, 
#                            created_at, processed_at
#                     FROM documents 
#                     WHERE scan_status = 'clean'
#                     ORDER BY created_at DESC
#                 """)
#                 rows = cur.fetchall()
        
#         documents = []
#         for row in rows:
#             documents.append({
#                 "id": row[0],
#                 "filename": row[2],  # Fixed: was row[1]
#                 "file_size": row[1],  # Fixed: was row[2]
#                 "scan_status": row[3],
#                 "is_processed": row[4],
#                 "created_at": row[4].isoformat() if row[4] else None,
#                 "processed_at": row[5].isoformat() if row[6] else None,
#                 "available_for_query": row[6]  # is_processed
#             })
        
#         return jsonify({
#             "documents": documents,
#             "total_count": len(documents),
#             "processed_count": sum(1 for doc in documents if doc['is_processed'])
#         }), 200
        
#     except Exception as e:
#         logger.error(f"List documents error: {e}")
#         return jsonify({"error": "Failed to list documents", "details": str(e)}), 500

# # Existing routes (unchanged)
# @app.route("/status/<doc_id>", methods=["GET"])
# def check_status(doc_id):
#     try:
#         with db_connect() as conn, conn.cursor() as cur:
#             cur.execute("""
#                 SELECT scan_status, scan_result, is_processed
#                 FROM documents WHERE id=%s
#             """, (doc_id,))
#             row = cur.fetchone()
#         if not row:
#             return jsonify({"error": "Document not found"}), 404
#         scan_status, scan_result, is_processed = row
#         return jsonify({
#             "scan_status": scan_status,
#             "scan_result": scan_result,
#             "ready_for_processing": scan_status == "clean" and not is_processed,
#             "rag_processed": is_processed,
#             "rag_available": rag_initialized
#         }), 200
#     except Exception as e:
#         logger.error(f"Status check error: {e}")
#         return jsonify({"error": "Status check failed", "details": str(e)}), 500

# if __name__ == "__main__":
#     init_dirs()
#     app.run(debug=False, host="127.0.0.1", port=5000)


# Flask Backend version 4 - RAG Integration (Error-Free with Enhanced Debugging)

import os
import uuid
import hashlib
import logging
import shutil
import subprocess
import io
import re
import html
from pathlib import Path
from flask import Flask, request, jsonify, render_template
import psycopg2
from werkzeug.utils import secure_filename
from psycopg2.extras import Json
from dotenv import load_dotenv
from flask_cors import CORS

# RAG-specific imports
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
# import numpy as np
import PyPDF2
import numpy as np
from pgvector.psycopg2 import register_vector

load_dotenv()

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "pdf_dms")
DB_USER = os.getenv("DB_USER", "dms_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aryan")
CLAMSCAN_PATH = os.getenv("CLAMSCAN_PATH", r"C:\Program Files\ClamAV\clamscan.exe")
FRESHCLAM_PATH = os.getenv("FRESHCLAM_PATH", r"C:\Program Files\ClamAV\freshclam.exe")
CLAMAV_DB_DIR = os.getenv("CLAMAV_DB_DIR", r"C:\Program Files\ClamAV\database")
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_SIZE", str(200 * 1024 * 1024)))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAKFNYPNWvZ1lefBXWYXzSbIBGjzqPD1DM")
ROOT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT_DIR / "pdf-questions-dms" / "uploads"
QUARANTINE_DIR = ROOT_DIR / "pdf-questions-dms" / "quarantine"
CLEAN_DIR = ROOT_DIR / "pdf-questions-dms" / "clean_uploads"
TEMP_DIR = ROOT_DIR / "temp"
LOG_DIR = ROOT_DIR / "logs"

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIMES = {"application/pdf"}

# Logging
LOG_DIR.mkdir(exist_ok=True, parents=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "security.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger("dms")

# Global variable to track RAG initialization
rag_pipeline = None
rag_initialized = False

# RAG Classes and Functions
class SecurityManager:
    @staticmethod
    def sanitize_input(text):
        """Sanitize user input to prevent prompt injection"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = html.escape(str(text))
        
        # Remove potential instruction keywords
        dangerous_patterns = [
            r'ignore\s+previous\s+instructions',
            r'system\s*:',
            r'assistant\s*:',
            r'<\s*/?system\s*>',
            r'<\s*/?assistant\s*>',
            r'pretend\s+to\s+be',
            r'act\s+as\s+if',
            r'roleplay\s+as'
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()

class DocumentProcessor:
    def __init__(self):
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Document processor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize document processor: {e}")
            raise e
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        continue
                        
            if not text.strip():
                raise ValueError("No readable text found in PDF")
                
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise e
        return text
    
    def chunk_text(self, text, chunk_size=500, overlap=50):
        """Split text into chunks for better retrieval"""
        if not text or not text.strip():
            return []
            
        words = text.split()
        if len(words) == 0:
            return []
            
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk.strip())
        
        return chunks
    
    def create_embeddings(self, text_chunks):
        """Generate embeddings for text chunks"""
        if not text_chunks:
            return np.array([])
            
        try:
            embeddings = self.embedding_model.encode(text_chunks)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise e

class VectorDatabase:
    def __init__(self):
        self.connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
        self.db_ready = False
        
    def get_connection(self):
        try:
            conn = psycopg2.connect(self.connection_string)
            register_vector(conn)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise e
    
    def ensure_database_schema(self):
        """Ensure all required columns exist in documents table"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if documents table exists
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'documents'
                        )
                    """)
                    if not cur.fetchone()[0]:
                        logger.warning("Documents table doesn't exist")
                        return False
                    
                    # Add missing columns to documents table
                    missing_columns = [
                        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                        ("processed_at", "TIMESTAMP"),
                        ("is_processed", "BOOLEAN DEFAULT FALSE")
                    ]
                    
                    for col_name, col_def in missing_columns:
                        cur.execute(f"""
                            SELECT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'documents' AND column_name = '{col_name}'
                            )
                        """)
                        
                        if not cur.fetchone()[0]:
                            logger.info(f"Adding missing column: {col_name}")
                            cur.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_def}")
                    
                    # Update existing records with created_at if null
                    cur.execute("""
                        UPDATE documents 
                        SET created_at = CURRENT_TIMESTAMP 
                        WHERE created_at IS NULL
                    """)
                    
                conn.commit()
                logger.info("Database schema validation completed")
                return True
                
        except Exception as e:
            logger.error(f"Database schema validation failed: {e}")
            return False
    
    def setup_database(self):
        """Create tables for storing document chunks and embeddings"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if pgvector extension exists
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    
                    # Create document_chunks table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS document_chunks (
                            id SERIAL PRIMARY KEY,
                            document_id VARCHAR(255),
                            chunk_index INTEGER,
                            chunk_text TEXT,
                            embedding vector(384),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create index for better performance (only if table is new or index doesn't exist)
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_indexes 
                                WHERE indexname = 'chunk_embedding_idx'
                            ) THEN
                                CREATE INDEX chunk_embedding_idx 
                                ON document_chunks USING ivfflat (embedding vector_cosine_ops)
                                WITH (lists = 100);
                            END IF;
                        END
                        $$;
                    """)
                    
                    # Add foreign key constraint if documents table exists
                    cur.execute("""
                        DO $$ 
                        BEGIN
                            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
                                IF NOT EXISTS (
                                    SELECT 1 FROM information_schema.table_constraints 
                                    WHERE constraint_name = 'fk_document_id'
                                ) THEN
                                    ALTER TABLE document_chunks 
                                    ADD CONSTRAINT fk_document_id 
                                    FOREIGN KEY (document_id) REFERENCES documents(id)
                                    ON DELETE CASCADE;
                                END IF;
                            END IF;
                        EXCEPTION
                            WHEN duplicate_object THEN NULL;
                        END $$;
                    """)
                    
                conn.commit()
                self.db_ready = True
                logger.info("Database setup completed successfully")
                
        except psycopg2.errors.InsufficientPrivilege as e:
            logger.error(f"Database permission error: {e}")
            logger.error("Please run the following SQL commands as a superuser:")
            logger.error("GRANT ALL ON SCHEMA public TO dms_user;")
            raise e
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            raise e
    
    def ensure_tables_exist(self):
        """Check if tables exist, create if they don't"""
        try:
            # First ensure documents table has required columns
            if not self.ensure_database_schema():
                return False
                
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'document_chunks'
                        )
                    """)
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        logger.warning("document_chunks table doesn't exist, attempting to create...")
                        self.setup_database()
                    else:
                        self.db_ready = True
                    
                    return True
        except Exception as e:
            logger.error(f"Failed to ensure tables exist: {e}")
            return False
    def store_document_chunks(self, document_id, chunks, embeddings):
        """Store document chunks and their embeddings"""
        if not self.db_ready:
            if not self.ensure_tables_exist():
                raise RuntimeError("Database not ready for storing chunks")
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                # First, delete any existing chunks for this document
                    cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
                
                # FIXED: Only insert into the columns we actually need
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        cur.execute("""
                        INSERT INTO document_chunks (document_id, chunk_index, chunk_text, embedding)
                        VALUES (%s, %s, %s, %s)
                    """, (document_id, i, chunk, embedding.tolist()))
                conn.commit()
                logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise e
    
    # def store_document_chunks(self, document_id, chunks, embeddings):
    #     """Store document chunks and their embeddings"""
    #     if not self.db_ready:
    #         if not self.ensure_tables_exist():
    #             raise RuntimeError("Database not ready for storing chunks")
                
    #     try:
    #         with self.get_connection() as conn:
    #             with conn.cursor() as cur:
    #                 # First, delete any existing chunks for this document
    #                 cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
                    
    #                 # Insert new chunks
    #                 for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    #                     cur.execute("""
    #                         INSERT INTO document_chunks (document_id, chunk_index, chunk_text, embedding)
    #                         VALUES (%s, %s, %s, %s)
    #                     """, (document_id, i, chunk, embedding.tolist()))
    #             conn.commit()
    #             logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
                
    #     except Exception as e:
    #         logger.error(f"Failed to store chunks: {e}")
    #         raise e
    def retrieve_similar_chunks(self, query_embedding, limit=5, document_id=None):
        """Retrieve most similar document chunks"""
        if not self.db_ready:
            if not self.ensure_tables_exist():
                raise RuntimeError("Database not ready for retrieving chunks")
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                # FIXED: Convert to numpy array and cast to vector type in SQL
                    if document_id:
                        cur.execute("""
                        SELECT dc.chunk_text, d.original_filename, 1 - (dc.embedding <=> %s::vector) as similarity
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE dc.document_id = %s
                        ORDER BY dc.embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, document_id, query_embedding, limit))
                    else:
                        cur.execute("""
                        SELECT dc.chunk_text, d.original_filename, 1 - (dc.embedding <=> %s::vector) as similarity
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE d.scan_status = 'clean' AND COALESCE(d.is_processed, false) = true
                        ORDER BY dc.embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, query_embedding, limit))
                
                    results = cur.fetchall()
                return results
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {e}")
            raise e

    # def retrieve_similar_chunks(self, query_embedding, limit=5, document_id=None):
    #     """Retrieve most similar document chunks"""
    #     if not self.db_ready:
    #         if not self.ensure_tables_exist():
    #             raise RuntimeError("Database not ready for retrieving chunks")
                
    #     try:
    #         with self.get_connection() as conn:
    #             with conn.cursor() as cur:
    #                 if document_id:
    #                     cur.execute("""
    #                         SELECT dc.chunk_text, d.original_filename, 1 - (dc.embedding <=> %s) as similarity
    #                         FROM document_chunks dc
    #                         JOIN documents d ON dc.document_id = d.id
    #                         WHERE dc.document_id = %s
    #                         ORDER BY dc.embedding <=> %s
    #                         LIMIT %s
    #                     """, (query_embedding.tolist(), document_id, query_embedding.tolist(), limit))
    #                 else:
    #                     cur.execute("""
    #                         SELECT dc.chunk_text, d.original_filename, 1 - (dc.embedding <=> %s) as similarity
    #                         FROM document_chunks dc
    #                         JOIN documents d ON dc.document_id = d.id
    #                         WHERE d.scan_status = 'clean' AND COALESCE(d.is_processed, false) = true
    #                         ORDER BY dc.embedding <=> %s
    #                         LIMIT %s
    #                     """, (query_embedding.tolist(), query_embedding.tolist(), limit))
                    
    #                 results = cur.fetchall()
    #                 return results
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve chunks: {e}")
    #         raise e

class RAGPipeline:
    def __init__(self):
        try:
            # Initialize Gemini
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            
            # Initialize components
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.vector_db = VectorDatabase()
            self.document_processor = DocumentProcessor()
            self.security_manager = SecurityManager()
            
            logger.info("RAG pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {e}")
            raise e
        
    def process_document_for_rag(self, document_id, file_path):
        """Process a clean document and store embeddings"""
        try:
            # Ensure database is ready
            if not self.vector_db.ensure_tables_exist():
                raise RuntimeError("Database not ready for RAG processing")
            
            # Extract text from PDF
            text = self.document_processor.extract_text_from_pdf(file_path)
            
            if not text.strip():
                raise ValueError("No text content found in PDF")
            
            # Chunk the text
            chunks = self.document_processor.chunk_text(text)
            
            if not chunks:
                raise ValueError("No valid chunks created from text")
            
            # Create embeddings
            embeddings = self.document_processor.create_embeddings(chunks)
            
            if embeddings.size == 0:
                raise ValueError("Failed to create embeddings")
            
            # Store in vector database
            self.vector_db.store_document_chunks(document_id, chunks, embeddings)
            
            # Update document as processed
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE documents SET is_processed = true, processed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (document_id,))
                conn.commit()
            
            logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"RAG processing failed for {document_id}: {e}")
            raise e
    
    def query_documents(self, user_query, document_id=None):
        """Main RAG query function"""
        try:
            # Ensure database is ready
            if not self.vector_db.ensure_tables_exist():
                raise RuntimeError("Database not ready for querying")
            
            # Sanitize input
            sanitized_query = self.security_manager.sanitize_input(user_query)
            
            if len(sanitized_query.strip()) < 3:
                raise ValueError("Query too short after sanitization")
            
            # Create query embedding
            query_embedding = self.embedding_model.encode([sanitized_query])[0]
            
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding)


            # Retrieve similar chunks
            similar_chunks = self.vector_db.retrieve_similar_chunks(
                query_embedding, limit=5, document_id=document_id
            )
            
            if not similar_chunks:
                return {
                    'answer': "No relevant information found in the documents.",
                    'sources': [],
                    'query': sanitized_query
                }
            
            # Prepare context from retrieved chunks
            context = "\n\n".join([f"Source: {chunk[1]}\nContent: {chunk}" for chunk in similar_chunks])
            
            # Create secure prompt with strict grounding
            prompt = self.create_grounded_prompt(sanitized_query, context)
            
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            return {
                'answer': response.text,
                'sources': [{'filename': chunk[1], 'similarity': round(chunk[2], 3)} for chunk in similar_chunks],
                'query': sanitized_query
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise e
    
    def create_grounded_prompt(self, query, context):
        """Create a secure prompt that prevents hallucination"""
        return f"""
        You are a document assistant. Answer the question based ONLY on the provided context.
        
        STRICT RULES:
        1. Only use information from the provided context below
        2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in the provided documents to answer this question."
        3. Do not make assumptions or add information not present in the context
        4. Always be factual and cite which source you're referencing
        5. Keep responses concise and relevant
        
        CONTEXT:
        {context}
        
        QUESTION: {query}
        
        ANSWER (based only on the context above):
        """

# Initialize RAG Pipeline with error handling
def initialize_rag_pipeline():
    """Initialize RAG pipeline with proper error handling"""
    global rag_pipeline, rag_initialized
    
    try:
        if not rag_initialized:
            logger.info("Initializing RAG pipeline...")
            rag_pipeline = RAGPipeline()
            rag_initialized = True
            logger.info("RAG pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        rag_pipeline = None
        rag_initialized = False

# Existing helper functions (unchanged)
def db_connect():
    try:
        return psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e

def init_dirs():
    for d in (UPLOAD_DIR, QUARANTINE_DIR, CLEAN_DIR, TEMP_DIR, LOG_DIR):
        d.mkdir(exist_ok=True, parents=True)

def get_file_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def extension_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def file_magic_mime(file_path: Path) -> str:
    try:
        import magic
        m = magic.Magic(mime=True)
        return m.from_file(str(file_path))
    except Exception as e:
        logger.warning(f"MIME detection failed or library unavailable: {e}")
        return ""

def log_security_event(event_type: str, details, document_id=None, user_id=None, ip_address=None):
    try:
        details_obj = details if isinstance(details, (dict, list)) else {"message": str(details)}
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_logs (event_type, document_id, user_id, details, ip_address)
                VALUES (%s, %s, %s, %s, %s)
            """, (event_type, document_id, user_id, Json(details_obj), ip_address))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log security event: {e} | {event_type} | {details}")

def clamav_db_present() -> bool:
    db_dir = Path(CLAMAV_DB_DIR)
    return db_dir.exists() and any(db_dir.iterdir())

def try_freshclam_once() -> tuple:
    try:
        if not Path(FRESHCLAM_PATH).exists():
            return False, "freshclam.exe not found"
        result = subprocess.run(
            [FRESHCLAM_PATH],
            capture_output=True,
            text=True,
            timeout=180,
            shell=False
        )
        ok = result.returncode == 0
        msg = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        return ok, msg.strip()
    except subprocess.TimeoutExpired:
        return False, "freshclam timed out"
    except Exception as e:
        return False, f"freshclam error: {e}"

def parse_clamscan_output(stdout: str, returncode: int) -> tuple:
    out = (stdout or "").strip()
    if "FOUND" in out:
        return (False, out)
    if returncode == 0:
        return (True, "Clean")
    if returncode == 1:
        return (False, out or "Virus found")
    return (False, out or f"Scan failed with code {returncode}")

def scan_with_clamscan(file_path: Path) -> tuple:
    if not Path(CLAMSCAN_PATH).exists():
        return False, f"clamscan.exe not found at {CLAMSCAN_PATH}"
    if not clamav_db_present():
        return False, f"ClamAV database missing at {CLAMAV_DB_DIR}. Run freshclam once."
    try:
        result = subprocess.run(
            [CLAMSCAN_PATH, "--no-summary", str(file_path)],
            capture_output=True,
            text=True,
            timeout=300,
            shell=False
        )
        stdout = result.stdout
        stderr = result.stderr.strip()
        is_clean, msg = parse_clamscan_output(stdout, result.returncode)
        if not is_clean and not msg:
            msg = stderr or "Unknown scan error"
        return is_clean, msg
    except subprocess.TimeoutExpired:
        return False, "Scan timeout"
    except Exception as e:
        return False, f"Scan error: {e}"

# Flask App
app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES

appHasRunBefore = False

# ENHANCED DEBUG LOGGING FOR RAG ENDPOINTS
@app.before_request
def log_request_info():
    if request.endpoint in ['query_documents', 'query_specific_document']:
        logger.info(f"=== DEBUG REQUEST INFO ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request endpoint: {request.endpoint}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request content length: {request.content_length}")
        logger.info(f"Request is_json: {request.is_json}")
        logger.info(f"Request data: {request.get_data()}")
        try:
            json_data = request.get_json(force=True)
            logger.info(f"Request JSON: {json_data}")
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
        logger.info(f"=== END DEBUG INFO ===")

@app.before_request
def setup():
    global appHasRunBefore
    if not appHasRunBefore:
        init_dirs()
        logger.info("Directories ensured.")
        if not clamav_db_present():
            ok, msg = try_freshclam_once()
            logger.info(f"freshclam attempted on startup: ok={ok} msg={(msg or '')[:400]}")
        
        # Initialize RAG pipeline
        initialize_rag_pipeline()
        appHasRunBefore = True

@app.route("/health", methods=["GET"])
def health():
    status = "ok" if Path(CLAMSCAN_PATH).exists() else "clamscan_not_found"
    db_ok = clamav_db_present()
    return jsonify({
        "status": status,
        "clamav_db_present": db_ok,
        "upload_dir": str(UPLOAD_DIR),
        "quarantine_dir": str(QUARANTINE_DIR),
        "clean_dir": str(CLEAN_DIR),
        "rag_enabled": rag_initialized,
        "rag_status": "initialized" if rag_initialized else "failed"
    }), 200

# Existing upload route (unchanged)
@app.route("/upload", methods=["POST"])
def upload_file():
    client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
    user_id = request.headers.get("X-User-ID", "anonymous")
    try:
        if "file" not in request.files:
            log_security_event("UPLOAD_REJECTED", {"reason": "No file provided"}, user_id=user_id, ip_address=client_ip)
            return jsonify({"error": "No file provided"}), 400
        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        original_filename = file.filename
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            log_security_event("UPLOAD_REJECTED", {"reason": "Invalid extension", "filename": original_filename}, user_id=user_id, ip_address=client_ip)
            return jsonify({"error": "Only PDF files are allowed"}), 400
        # Save to quarantine first with UUID name
        doc_id = str(uuid.uuid4())
        quarantine_path = QUARANTINE_DIR / f"{doc_id}.pdf"
        file.save(quarantine_path)
        # Size check (defense-in-depth)
        if quarantine_path.stat().st_size > MAX_FILE_BYTES:
            quarantine_path.unlink(missing_ok=True)
            log_security_event("UPLOAD_REJECTED", {"reason": "Too large", "limit": MAX_FILE_BYTES}, user_id=user_id, ip_address=client_ip)
            return jsonify({"error": "File too large"}), 413
        # MIME best-effort check
        detected_mime = file_magic_mime(quarantine_path)
        if detected_mime and detected_mime not in ALLOWED_MIMES:
            quarantine_path.unlink(missing_ok=True)
            log_security_event("UPLOAD_REJECTED", {"reason": "MIME mismatch", "mime": detected_mime, "filename": original_filename}, user_id=user_id, ip_address=client_ip)
            return jsonify({"error": "File is not a valid PDF"}), 400
        file_hash = get_file_hash(quarantine_path)
        file_size = quarantine_path.stat().st_size
        # Insert DB record as pending - FIXED TO INCLUDE created_at
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (id, original_filename, file_path, file_hash, file_size, owner_id, scan_status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (doc_id, original_filename, str(quarantine_path), file_hash, file_size, user_id, "pending"))
            conn.commit()
        log_security_event("FILE_UPLOADED", {"filename": original_filename, "size": file_size}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        # Synchronous scan
        is_clean, scan_msg = scan_with_clamscan(quarantine_path)
        with db_connect() as conn, conn.cursor() as cur:
            if is_clean:
                # Move to clean directory
                clean_path = CLEAN_DIR / quarantine_path.name
                CLEAN_DIR.mkdir(exist_ok=True, parents=True)
                shutil.move(str(quarantine_path), str(clean_path))
                cur.execute("""
                    UPDATE documents
                    SET scan_status=%s, scan_result=%s, file_path=%s
                    WHERE id=%s
                """, ("clean", scan_msg, str(clean_path), doc_id))
                conn.commit()
                log_security_event("FILE_SCAN_CLEAN", {"result": scan_msg}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
                return jsonify({"document_id": doc_id, "status": "clean", "message": "File scanned clean and ready for processing"}), 200
            else:
                # Keep in quarantine; mark infected or error
                cur.execute("""
                    UPDATE documents
                    SET scan_status=%s, scan_result=%s
                    WHERE id=%s
                """, ("infected", scan_msg, doc_id))
                conn.commit()
                log_security_event("FILE_SCAN_INFECTED", {"result": scan_msg}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
                hint = "Virus DB missing. Run freshclam once (as Admin) in C:\\Program Files\\ClamAV." if "database missing" in scan_msg.lower() else None
                return jsonify({
                    "document_id": doc_id,
                    "status": "infected",
                    "error": "File failed antivirus scan",
                    "details": scan_msg,
                    "hint": hint
                }), 400
    except Exception as e:
        logger.exception("Upload error")
        log_security_event("UPLOAD_ERROR", {"error": str(e)}, user_id=user_id, ip_address=client_ip)
        return jsonify({"error": "Upload failed"}), 500

# NEW RAG ROUTES

@app.route("/setup-database", methods=["POST"])
def setup_database():
    """Manually trigger database setup"""
    if not rag_initialized:
        return jsonify({
            "error": "RAG system not initialized",
            "message": "Please restart the application"
        }), 503
    
    try:
        rag_pipeline.vector_db.setup_database()
        return jsonify({"message": "Database setup completed successfully"}), 200
    except Exception as e:
        return jsonify({
            "error": "Database setup failed", 
            "details": str(e),
            "solution": "Run as postgres superuser: GRANT ALL ON SCHEMA public TO dms_user;"
        }), 500

@app.route("/process-document/<doc_id>", methods=["POST"])
def process_document_for_rag(doc_id):
    """Process a clean document for RAG functionality"""
    if not rag_initialized:
        return jsonify({
            "error": "RAG system not available",
            "message": "RAG pipeline failed to initialize. Check logs for details."
        }), 503
    
    client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    try:
        # Check if document exists and is clean - FIXED QUERY
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT scan_status, file_path, COALESCE(is_processed, false) as is_processed, original_filename
                    FROM documents WHERE id = %s
                """, (doc_id,))
                row = cur.fetchone()
        
        if not row:
            return jsonify({"error": "Document not found"}), 404
        
        scan_status, file_path, is_processed, original_filename = row
        
        if scan_status != "clean":
            return jsonify({"error": "Document must be scanned clean before processing"}), 400
        
        if is_processed:
            return jsonify({"message": "Document already processed for RAG"}), 200
        
        # Process document with RAG pipeline
        chunk_count = rag_pipeline.process_document_for_rag(doc_id, file_path)
        
        log_security_event("DOCUMENT_PROCESSED_RAG", {
            "filename": original_filename,
            "chunk_count": chunk_count
        }, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        
        return jsonify({
            "message": f"Document processed successfully for RAG with {chunk_count} chunks",
            "document_id": doc_id,
            "chunk_count": chunk_count
        }), 200
        
    except Exception as e:
        logger.error(f"RAG processing error for {doc_id}: {e}")
        log_security_event("DOCUMENT_PROCESSING_ERROR", {
            "error": str(e)
        }, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        return jsonify({"error": "Document processing failed", "details": str(e)}), 500

@app.route("/query", methods=["POST"])
def query_documents():
    """Query all processed documents using RAG"""
    if not rag_initialized:
        return jsonify({
            "error": "RAG system not available",
            "message": "RAG pipeline failed to initialize. Check logs for details."
        }), 503
    
    client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    try:
        # Enhanced JSON validation
        if not request.is_json:
            logger.error(f"Request is not JSON. Content-Type: {request.content_type}")
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        logger.info(f"Received JSON data: {data}")
        
        if not data:
            logger.error("Empty JSON data received")
            return jsonify({'error': 'Empty JSON data'}), 400
        
        if 'query' not in data:
            logger.error(f"Missing 'query' field in data: {data}")
            return jsonify({'error': 'Query field is required'}), 400
        
        user_query = data['query']
        if not user_query or not isinstance(user_query, str):
            return jsonify({'error': 'Query must be a non-empty string'}), 400
        
        user_query = user_query.strip()
        
        # Input validation
        if len(user_query) > 500:
            return jsonify({'error': 'Query too long (max 500 characters)'}), 400
        
        if len(user_query) < 3:
            return jsonify({'error': 'Query too short (min 3 characters)'}), 400
        
        # Process query with RAG pipeline
        result = rag_pipeline.query_documents(user_query)
        
        log_security_event("DOCUMENT_QUERY", {
            "original_query": user_query,
            "sanitized_query": result.get('query', ''),
            "sources_count": len(result.get('sources', []))
        }, user_id=user_id, ip_address=client_ip)
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": "Validation failed", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"Query error: {e}")
        log_security_event("QUERY_ERROR", {"error": str(e)}, user_id=user_id, ip_address=client_ip)
        return jsonify({"error": "Query processing failed", "details": str(e)}), 500

@app.route("/query-document/<doc_id>", methods=["POST"])
def query_specific_document(doc_id):
    """Query a specific document using RAG - ENHANCED WITH DEBUGGING"""
    logger.info(f"=== QUERY SPECIFIC DOCUMENT START ===")
    logger.info(f"Document ID: {doc_id}")
    
    if not rag_initialized:
        logger.error("RAG system not available")
        return jsonify({
            "error": "RAG system not available",
            "message": "RAG pipeline failed to initialize. Check logs for details."
        }), 503
    
    client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    try:
        # Enhanced JSON validation
        logger.info(f"Request is_json: {request.is_json}")
        logger.info(f"Request content_type: {request.content_type}")
        
        if not request.is_json:
            logger.error(f"Request is not JSON. Content-Type: {request.content_type}")
            return jsonify({'error': 'Request must be JSON', 'received_content_type': request.content_type}), 400
        
        data = request.get_json()
        logger.info(f"Received JSON data: {data}")
        
        if not data:
            logger.error("Empty JSON data received")
            return jsonify({'error': 'Empty JSON data'}), 400
        
        if 'query' not in data:
            logger.error(f"Missing 'query' field in data: {data}")
            return jsonify({'error': 'Query field is required', 'received_data': data}), 400
        
        user_query = data['query']
        if not user_query or not isinstance(user_query, str):
            logger.error(f"Invalid query type or empty: {type(user_query)} - {user_query}")
            return jsonify({'error': 'Query must be a non-empty string', 'received_query': str(user_query)}), 400
        
        user_query = user_query.strip()
        logger.info(f"Processed user query: '{user_query}'")
        
        # Input validation
        if len(user_query) > 500:
            return jsonify({'error': 'Query too long (max 500 characters)'}), 400
        
        if len(user_query) < 3:
            return jsonify({'error': 'Query too short (min 3 characters)'}), 400
        
        # Check if document exists and is processed - ENHANCED QUERY
        logger.info(f"Checking document status for {doc_id}")
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT scan_status, COALESCE(is_processed, false) as is_processed, original_filename
                    FROM documents WHERE id = %s
                """, (doc_id,))
                row = cur.fetchone()
        
        if not row:
            logger.error(f"Document not found: {doc_id}")
            return jsonify({"error": "Document not found"}), 404
        
        scan_status, is_processed, original_filename = row
        logger.info(f"Document status - scan_status: {scan_status}, is_processed: {is_processed}, filename: {original_filename}")
        
        if scan_status != "clean":
            logger.error(f"Document not clean: {scan_status}")
            return jsonify({"error": "Document must be scanned clean before querying"}), 400
        
        if not is_processed:
            logger.error(f"Document not processed for RAG")
            return jsonify({
                "error": "Document must be processed for RAG before querying",
                "suggestion": "Please process this document first using the /process-document endpoint"
            }), 400
        
        logger.info(f"Document is ready for querying. Processing query: '{user_query}'")
        
        # Process query with RAG pipeline for specific document
        result = rag_pipeline.query_documents(user_query, document_id=doc_id)
        logger.info(f"Query result: {result}")
        
        log_security_event("SPECIFIC_DOCUMENT_QUERY", {
            "filename": original_filename,
            "original_query": user_query,
            "sanitized_query": result.get('query', ''),
            "sources_count": len(result.get('sources', []))
        }, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        
        logger.info(f"=== QUERY SPECIFIC DOCUMENT SUCCESS ===")
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": "Validation failed", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"Specific document query error: {e}")
        logger.exception("Full stack trace:")
        log_security_event("SPECIFIC_QUERY_ERROR", {"error": str(e)}, document_id=doc_id, user_id=user_id, ip_address=client_ip)
        return jsonify({"error": "Query processing failed", "details": str(e)}), 500

@app.route("/documents", methods=["GET"])
def list_documents():
    """List all processed documents available for querying - FIXED COLUMN ORDER"""
    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, original_filename, file_size, scan_status, 
                           COALESCE(is_processed, false) as is_processed, 
                           created_at, processed_at
                    FROM documents 
                    WHERE scan_status = 'clean'
                    ORDER BY created_at DESC
                """)
                rows = cur.fetchall()
        
        documents = []
        for row in rows:
            documents.append({
                "id": row[0],
                "filename": row[2],  # FIXED: original_filename is index 1
                "file_size": row[1],  # FIXED: file_size is index 2
                "scan_status": row[3],
                "is_processed": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "processed_at": row[6].isoformat() if row[6] else None,
                "available_for_query": row[4]  # is_processed
            })
        
        return jsonify({
            "documents": documents,
            "total_count": len(documents),
            "processed_count": sum(1 for doc in documents if doc['is_processed'])
        }), 200
        
    except Exception as e:
        logger.error(f"List documents error: {e}")
        return jsonify({"error": "Failed to list documents", "details": str(e)}), 500

@app.route("/status/<doc_id>", methods=["GET"])
def check_status(doc_id):
    try:
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT scan_status, scan_result, COALESCE(is_processed, false) as is_processed
                FROM documents WHERE id=%s
            """, (doc_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Document not found"}), 404
        scan_status, scan_result, is_processed = row
        return jsonify({
            "scan_status": scan_status,
            "scan_result": scan_result,
            "ready_for_processing": scan_status == "clean" and not is_processed,
            "rag_processed": is_processed,
            "rag_available": rag_initialized
        }), 200
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"error": "Status check failed", "details": str(e)}), 500

if __name__ == "__main__":
    init_dirs()
    app.run(debug=False, host="127.0.0.1", port=5000)
