
# import os
# import hashlib
# # import test
# import magic
# import subprocess
# import uuid
# from pathlib import Path
# from flask import Flask, request, jsonify
# import psycopg2
# from datetime import datetime
# import logging
# import json

# # Configure logging
# log_dir = Path("logs")
# log_dir.mkdir(exist_ok=True)

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler(log_dir / 'security.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# app = Flask(__name__)
# app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# # Configuration
# CLAMAV_PATH = r"C:\Program Files\ClamAV\clamdscan.exe"
# UPLOAD_DIR = Path("pdf-questions-dms/uploads")
# QUARANTINE_DIR = Path("pdf-questions-dms/quarantine") 
# CLEAN_DIR = Path("pdf-questions-dms/clean_uploads")
# ALLOWED_EXTENSIONS = {'.pdf'}
# ALLOWED_MIMES = {'application/pdf'}

# def get_file_hash(file_path):
#     """Generate SHA-256 hash - same as Linux version."""
#     hasher = hashlib.sha256()
#     with open(file_path, 'rb') as f:
#         for chunk in iter(lambda: f.read(4096), b""):
#             hasher.update(chunk)
#     return hasher.hexdigest()

# # def validate_file_type(file_path):
# #     """Validate file type using magic bytes."""
# #     mime = test.Magic(mime=True)
# #     detected_mime = mime.from_file(str(file_path))
# #     return detected_mime in ALLOWED_MIMES

# def validate_file_type(file_path):
#     """Validate file type using magic bytes."""
#     mime = magic.Magic(mime=True)
#     detected_mime = mime.from_file(str(file_path))
#     return detected_mime in ALLOWED_MIMES

# def scan_with_clamav(file_path):
#     """Scan file with ClamAV on Windows."""
#     try:
#         # Windows command for ClamAV daemon scan
#         result = subprocess.run(
#             [CLAMAV_PATH, '--no-summary', str(file_path)],
#             capture_output=True,
#             text=True,
#             timeout=30,
#             shell=False
#         )
        
#         if result.returncode == 0:
#             return True, "Clean"
#         else:
#             return False, result.stdout.strip()
            
#     except subprocess.TimeoutExpired:
#         return False, "Scan timeout"
#     except FileNotFoundError:
#         logger.error("ClamAV not found. Install ClamAV and update CLAMAV_PATH")
#         return False, "Scanner not available"
#     except Exception as e:
#         logger.error(f"ClamAV scan error: {e}")
#         return False, f"Scan error: {e}"

# # def log_security_event(event_type, details, document_id=None, user_id=None, ip_address=None):
# #     """Log security events to database."""
# #     try:
# #         conn = psycopg2.connect(
# #             host="localhost",
# #             database="pdf_dms",
# #             user="dms_user",
# #             password="your_secure_password_here"
# #             # password="aryan"
# #         )
# #         cur = conn.cursor()
        
# #         cur.execute("""
# #             INSERT INTO audit_logs (event_type, document_id, user_id, details, ip_address)
# #             VALUES (%s, %s, %s, %s, %s)
# #         """, (event_type, document_id, user_id, details, ip_address))
        
# #         conn.commit()
# #         cur.close()
# #         conn.close()
        
# #     except Exception as e:
# #         logger.error(f"Failed to log security event: {e}")

# def log_security_event(event_type, details, document_id=None, user_id=None, ip_address=None):
#     """Log security events to database."""
#     try:
#         if isinstance(details, dict):
#             details = json.dumps(details)

#         conn = psycopg2.connect(
#             host="localhost",
#             database="pdf_dms",
#             user="dms_user",
#             password="your_secure_password_here"
#         )
#         cur = conn.cursor()
        
#         cur.execute("""
#             INSERT INTO audit_logs (event_type, document_id, user_id, details, ip_address)
#             VALUES (%s, %s, %s, %s, %s)
#         """, (event_type, document_id, user_id, details, ip_address))
        
#         conn.commit()
#         cur.close()
#         conn.close()
        
#     except Exception as e:
#         logger.error(f"Failed to log security event: {e}")

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     """Secure file upload endpoint."""
    
#     # Get client IP for logging
#     client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
#     user_id = request.headers.get('X-User-ID', 'anonymous')  # Add proper auth
    
#     try:
#         # Check if file is present
#         if 'file' not in request.files:
#             log_security_event('UPLOAD_REJECTED', {'reason': 'No file provided'}, 
#                              user_id=user_id, ip_address=client_ip)
#             return jsonify({'error': 'No file provided'}), 400
        
#         file = request.files['file']
#         if file.filename == '':
#             return jsonify({'error': 'No file selected'}), 400
        
#         # Validate filename and extension
#         original_filename = file.filename
#         file_ext = Path(original_filename).suffix.lower()
        
#         if file_ext not in ALLOWED_EXTENSIONS:
#             log_security_event('UPLOAD_REJECTED', 
#                              {'reason': 'Invalid extension', 'filename': original_filename},
#                              user_id=user_id, ip_address=client_ip)
#             return jsonify({'error': 'Only PDF files are allowed'}), 400
        
#         # Generate secure filename
#         doc_id = str(uuid.uuid4())
#         secure_filename = f"{doc_id}.pdf"
#         quarantine_path = QUARANTINE_DIR / secure_filename
        
#         # Save to quarantine first
#         file.save(quarantine_path)
        
#         # Get file info
#         file_size = quarantine_path.stat().st_size
#         file_hash = get_file_hash(quarantine_path)
        
#         # Validate file type with magic bytes
#         if not validate_file_type(quarantine_path):
#             quarantine_path.unlink()  # Delete invalid file
#             log_security_event('UPLOAD_REJECTED', 
#                              {'reason': 'Invalid file type', 'filename': original_filename},
#                              user_id=user_id, ip_address=client_ip)
#             return jsonify({'error': 'File is not a valid PDF'}), 400
        
#         # Save to database with pending status
#         conn = psycopg2.connect(
#             host="localhost",
#             database="pdf_dms",
#             user="dms_user", 
#             password="your_secure_password_here"
#         )
#         cur = conn.cursor()
        
#         cur.execute("""
#             INSERT INTO documents (id, original_filename, file_path, file_hash, 
#                                  file_size, owner_id, scan_status)
#             VALUES (%s, %s, %s, %s, %s, %s, %s)
#         """, (doc_id, original_filename, str(quarantine_path), file_hash,
#               file_size, user_id, 'pending'))
        
#         conn.commit()
#         cur.close()
#         conn.close()
        
#         # Log successful upload
#         log_security_event('FILE_UPLOADED', 
#                          {'filename': original_filename, 'size': file_size},
#                          document_id=doc_id, user_id=user_id, ip_address=client_ip)
        
#         # Trigger async scanning (you can use Celery, or simple background thread)
#         scan_file_async(doc_id, quarantine_path, user_id, client_ip)
        
#         return jsonify({
#             'document_id': doc_id,
#             'status': 'uploaded',
#             'message': 'File uploaded successfully, scanning in progress'
#         }), 200
        
#     except Exception as e:
#         logger.error(f"Upload error: {e}")
#         log_security_event('UPLOAD_ERROR', {'error': str(e)},
#                          user_id=user_id, ip_address=client_ip)
#         return jsonify({'error': 'Upload failed'}), 500

# def scan_file_async(doc_id, file_path, user_id, client_ip):
#     """Background file scanning (implement with proper async handling)."""
    
#     # Scan with ClamAV
#     is_clean, scan_result = scan_with_clamav(file_path)
    
#     # Update database
#     conn = psycopg2.connect(
#         host="localhost",
#         database="pdf_dms",
#         user="dms_user",
#         password="your_secure_password_here"
#     )
#     cur = conn.cursor()
    
#     if is_clean:
#         # Move to clean directory
#         clean_path = CLEAN_DIR / file_path.name
#         file_path.rename(clean_path)
        
#         cur.execute("""
#             UPDATE documents 
#             SET scan_status = %s, scan_result = %s, file_path = %s
#             WHERE id = %s
#         """, ('clean', scan_result, str(clean_path), doc_id))
        
#         log_security_event('FILE_SCAN_CLEAN', 
#                          {'result': scan_result},
#                          document_id=doc_id, user_id=user_id, ip_address=client_ip)
#     else:
#         # Mark as infected and quarantine
#         cur.execute("""
#             UPDATE documents 
#             SET scan_status = %s, scan_result = %s
#             WHERE id = %s
#         """, ('infected', scan_result, doc_id))
        
#         log_security_event('FILE_SCAN_INFECTED', 
#                          {'result': scan_result},
#                          document_id=doc_id, user_id=user_id, ip_address=client_ip)
    
#     conn.commit()
#     cur.close()
#     conn.close()

# @app.route('/status/<doc_id>')
# def check_status(doc_id):
#     """Check file scan status."""
#     try:
#         conn = psycopg2.connect(
#             host="localhost",
#             database="pdf_dms",
#             user="dms_user",
#             password="your_secure_password_here"
#         )
#         cur = conn.cursor()
        
#         cur.execute("""
#             SELECT scan_status, scan_result, is_processed
#             FROM documents WHERE id = %s
#         """, (doc_id,))
        
#         result = cur.fetchone()
#         cur.close()
#         conn.close()
        
#         if result:
#             status, scan_result, is_processed = result
#             return jsonify({
#                 'scan_status': status,
#                 'scan_result': scan_result,
#                 'ready_for_processing': status == 'clean' and not is_processed
#             })
#         else:
#             return jsonify({'error': 'Document not found'}), 404
            
#     except Exception as e:
#         logger.error(f"Status check error: {e}")
#         return jsonify({'error': 'Status check failed'}), 500

# if __name__ == '__main__':
#     # Ensure directories exist
#     for directory in [UPLOAD_DIR, QUARANTINE_DIR, CLEAN_DIR, Path("temp"), Path("logs")]:
#         directory.mkdir(exist_ok=True)
    

#     # Run in development mode
#     app.run(debug=False, host='127.0.0.1', port=5000)

