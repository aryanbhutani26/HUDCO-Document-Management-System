# # Local Pipeline version 2 
import os
import uuid
import json
import hashlib
import logging
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "pdf_dms")
DB_USER = os.getenv("DB_USER", "dms_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_secure_password_here")

# ClamAV binaries (no daemon)
CLAMSCAN_PATH = os.getenv("CLAMSCAN_PATH", r"C:\Program Files\ClamAV\clamscan.exe")
FRESHCLAM_PATH = os.getenv("FRESHCLAM_PATH", r"C:\Program Files\ClamAV\freshclam.exe")
CLAMAV_DB_DIR = os.getenv("CLAMAV_DB_DIR", r"C:\Program Files\ClamAV\database")

# Max upload 50MB
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))

# Working directories (relative to project root)
ROOT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT_DIR / "pdf-questions-dms" / "uploads"
QUARANTINE_DIR = ROOT_DIR / "pdf-questions-dms" / "quarantine"
CLEAN_DIR = ROOT_DIR / "pdf-questions-dms" / "clean_uploads"
TEMP_DIR = ROOT_DIR / "temp"
LOG_DIR = ROOT_DIR / "logs"

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIMES = {"application/pdf"}  # best-effort on Windows

# ---------------------------
# Logging
# ---------------------------
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

# ---------------------------
# Helpers
# ---------------------------
def db_connect():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

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
    # python-magic-bin for Windows; be resilient if missing
    
    try:
        import magic
        m = magic.Magic(mime=True)
        return m.from_file(str(file_path))
    except Exception as e:
        logger.warning(f"MIME detection failed or library unavailable: {e}")
        return ""

def log_security_event(event_type: str, details, document_id=None, user_id=None, ip_address=None):
    try:
        # Ensure details is a JSON object in DB
        if not isinstance(details, (dict, list)):
            details_obj = {"message": str(details)}
        else:
            details_obj = details

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

def try_freshclam_once() -> tuple[bool, str]:
    try:
        if not Path(FRESHCLAM_PATH).exists():
            return False, "freshclam.exe not found"
        # Run freshclam (may need Admin if Program Files permissions block writing)
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

def parse_clamscan_output(stdout: str, returncode: int) -> tuple[bool, str]:
    """
    clamscan return codes:
      0: no virus found
      1: virus(es) found
      2: error
    We'll check "FOUND" in stdout for infection details.
    """
    out = (stdout or "").strip()
    if "FOUND" in out:
        return (False, out)
    if returncode == 0:
        return (True, "Clean")
    if returncode == 1:
        # Virus found but maybe not "FOUND" present (rare); treat as infected
        return (False, out or "Virus found")
    # returncode == 2 or other -> error
    return (False, out or f"Scan failed with code {returncode}")

def scan_with_clamscan(file_path: Path) -> tuple[bool, str]:
    """
    Return (is_clean, message)
    Uses clamscan.exe --no-summary <file>.
    Detects missing database and reports guidance.
    """
    if not Path(CLAMSCAN_PATH).exists():
        return False, f"clamscan.exe not found at {CLAMSCAN_PATH}"

    # Quick missing DB check to avoid confusing output
    if not clamav_db_present():
        return False, f"ClamAV database missing at {CLAMAV_DB_DIR}. Run freshclam once."

    try:
        result = subprocess.run(
            [CLAMSCAN_PATH, "--no-summary", str(file_path)],
            capture_output=True,
            text=True,
            timeout=90,
            shell=False
        )
        stdout = result.stdout
        stderr = result.stderr.strip()

        # Known symptom when DB missing -> Known viruses: 0; but we pre-check above
        is_clean, msg = parse_clamscan_output(stdout, result.returncode)
        if not is_clean and not msg:
            msg = stderr or "Unknown scan error"
        return is_clean, msg
    except subprocess.TimeoutExpired:
        return False, "Scan timeout"
    except Exception as e:
        return False, f"Scan error: {e}"

# ---------------------------
# Flask app
# ---------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES

# @app.before_first_request
# def setup():
#     init_dirs()
#     logger.info("Directories ensured.")
#     # Optional: populate DB once if empty
#     if not clamav_db_present():
#         ok, msg = try_freshclam_once()
#         logger.info(f"freshclam attempted on startup: ok={ok} msg={(msg or '')[:400]}")


appHasRunBefore = False

@app.before_request
def setup():
    global appHasRunBefore
    if not appHasRunBefore:
        init_dirs()
        logger.info("Directories ensured.")
        # Optional: populate DB once if empty
        if not clamav_db_present():
            ok, msg = try_freshclam_once()
            logger.info(f"freshclam attempted on startup: ok={ok} msg={(msg or '')[:400]}")
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
    }), 200

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

        # Insert DB record as pending
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (id, original_filename, file_path, file_hash, file_size, owner_id, scan_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (doc_id, original_filename, str(quarantine_path), file_hash, file_size, user_id, "pending"))
            conn.commit()

        log_security_event("FILE_UPLOADED", {"filename": original_filename, "size": file_size}, document_id=doc_id, user_id=user_id, ip_address=client_ip)

        # Synchronous scan (swap to background worker later if desired)
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

                # Helpful guidance if DB missing
                if "database missing" in scan_msg.lower():
                    hint = "Virus DB missing. Run freshclam once (as Admin) in C:\\Program Files\\ClamAV."
                else:
                    hint = None

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

@app.route("/status/<doc_id>", methods=["GET"])
def check_status(doc_id):
    try:
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT scan_status, scan_result, is_processed
                FROM documents WHERE id=%s
            """, (doc_id,))
            row = cur.fetchone()

        if not row:
            return jsonify({"error": "Document not found"}), 404

        scan_status, scan_result, is_processed = row
        return jsonify({
            "scan_status": scan_status,
            "scan_result": scan_result,
            "ready_for_processing": scan_status == "clean" and not is_processed
        }), 200
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"error": "Status check failed"}), 500

if __name__ == "__main__":
    init_dirs()
    app.run(debug=False, host="127.0.0.1", port=5000)

