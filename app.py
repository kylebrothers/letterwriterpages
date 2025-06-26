from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
import os
import logging
from datetime import datetime
import uuid
import io
from docx import Document
import PyPDF2

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = None  # Will be set up with Redis connection
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'promotion-letters:'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Redis connection for sessions and rate limiting
try:
    import redis
    redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
    app.config['SESSION_REDIS'] = redis_client
    logger.info("Redis connection established")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    # Fallback to filesystem sessions for development
    app.config['SESSION_TYPE'] = 'filesystem'

# Initialize session management
Session(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=os.environ.get('RATE_LIMIT_STORAGE_URL', 'redis://redis:6379'),
    default_limits=["100 per hour"]
)

# Initialize Claude client
try:
    claude_client = anthropic.Anthropic(
        api_key=os.environ.get('CLAUDE_API_KEY')
    )
    logger.info("Claude API client initialized")
except Exception as e:
    logger.error(f"Failed to initialize Claude client: {e}")
    claude_client = None

# File processing functions
def extract_text_from_docx(file_stream):
    """Extract text from Word document"""
    try:
        doc = Document(file_stream)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Skip empty paragraphs
                text.append(paragraph.text.strip())
        
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    text.append(' | '.join(row_text))
        
        return '\n'.join(text)
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        raise ValueError(f"Failed to extract text from Word document: {str(e)}")

def extract_text_from_pdf(file_stream):
    """Extract text from PDF document"""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    text.append(f"--- Page {page_num + 1} ---")
                    text.append(page_text.strip())
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                continue
        
        if not text:
            raise ValueError("No text could be extracted from the PDF")
        
        return '\n'.join(text)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to extract text from PDF document: {str(e)}")

def process_uploaded_file(file):
    """Process uploaded file and extract text"""
    if not file or not file.filename:
        return None
    
    filename = file.filename.lower()
    file_content = file.read()
    
    if not file_content:
        raise ValueError("File is empty")
    
    file_stream = io.BytesIO(file_content)
    
    if filename.endswith('.docx'):
        return extract_text_from_docx(file_stream)
    elif filename.endswith('.pdf'):
        return extract_text_from_pdf(file_stream)
    else:
        raise ValueError(f"Unsupported file type. Please upload .docx or .pdf files only.")

def validate_file(file):
    """Validate uploaded file"""
    if not file or not file.filename:
        return False, "No file provided"
    
    filename = file.filename.lower()
    if not (filename.endswith('.docx') or filename.endswith('.pdf')):
        return False, "Only .docx and .pdf files are supported"
    
    # Check file size (this is also enforced by Flask config)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if size > 10 * 1024 * 1024:  # 10MB
        return False, "File size must be less than 10MB"
    
    if size == 0:
        return False, "File is empty"
    
    return True, "File is valid"

# Utility function to generate session ID
def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

# Home page
@app.route('/')
def home():
    session_id = get_session_id()
    logger.info(f"Home page accessed - Session: {session_id}")
    return render_template('home.html')

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'claude_available': claude_client is not None
    })

# Chairs Promotion Letter
@app.route('/chairs-promotion-letter')
def chairs_promotion_letter():
    session_id = get_session_id()
    logger.info(f"Chairs promotion letter page accessed - Session: {session_id}")
    return render_template('chairs_promotion_letter.html')

@app.route('/api/chairs-promotion-letter', methods=['POST'])
@limiter.limit("5 per minute")
def api_chairs_promotion_letter():
    if not claude_client:
        return jsonify({'error': 'Claude API not available'}), 503
    
    try:
        # Handle file uploads
        uploaded_files_text = {}
        
        # Process CV upload
        if 'cv_file' in request.files:
            cv_file = request.files['cv_file']
            is_valid, message = validate_file(cv_file)
            if cv_file.filename and not is_valid:
                return jsonify({'error': f'CV file error: {message}'}), 400
            if cv_file.filename and is_valid:
                try:
                    uploaded_files_text['cv'] = process_uploaded_file(cv_file)
                    logger.info(f"CV file processed: {cv_file.filename}")
                except Exception as e:
                    return jsonify({'error': f'Error processing CV file: {str(e)}'}), 400
        
        # Process teaching evaluations upload
        if 'teaching_file' in request.files:
            teaching_file = request.files['teaching_file']
            is_valid, message = validate_file(teaching_file)
            if teaching_file.filename and not is_valid:
                return jsonify({'error': f'Teaching evaluations file error: {message}'}), 400
            if teaching_file.filename and is_valid:
                try:
                    uploaded_files_text['teaching'] = process_uploaded_file(teaching_file)
                    logger.info(f"Teaching evaluations file processed: {teaching_file.filename}")
                except Exception as e:
                    return jsonify({'error': f'Error processing teaching evaluations file: {str(e)}'}), 400
        
        # Handle form data
        form_data = request.form.to_dict()
        session_id = get_session_id()
        
        logger.info(f"Chairs promotion letter API called - Session: {session_id}")
        
        # TODO: Implement Claude API call with form_data and uploaded_files_text
        # This is where you'll add the specific Claude prompt and logic
        
        return jsonify({
            'success': True,
            'message': 'Chairs promotion letter endpoint ready',
            'session_id': session_id,
            'files_processed': list(uploaded_files_text.keys()),
            'form_data_received': list(form_data.keys())
        })
    
    except Exception as e:
        logger.error(f"Error in chairs promotion letter API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Faculty Promotion Letter
@app.route('/faculty-promotion-letter')
def faculty_promotion_letter():
    session_id = get_session_id()
    logger.info(f"Faculty promotion letter page accessed - Session: {session_id}")
    return render_template('faculty_promotion_letter.html')

@app.route('/api/faculty-promotion-letter', methods=['POST'])
@limiter.limit("5 per minute")
def api_faculty_promotion_letter():
    if not claude_client:
        return jsonify({'error': 'Claude API not available'}), 503
    
    try:
        # Handle file uploads
        uploaded_files_text = {}
        
        # Process CV upload
        if 'cv_file' in request.files:
            cv_file = request.files['cv_file']
            is_valid, message = validate_file(cv_file)
            if cv_file.filename and not is_valid:
                return jsonify({'error': f'CV file error: {message}'}), 400
            if cv_file.filename and is_valid:
                try:
                    uploaded_files_text['cv'] = process_uploaded_file(cv_file)
                    logger.info(f"CV file processed: {cv_file.filename}")
                except Exception as e:
                    return jsonify({'error': f'Error processing CV file: {str(e)}'}), 400
        
        # Process publications/work samples upload
        if 'publications_file' in request.files:
            pub_file = request.files['publications_file']
            is_valid, message = validate_file(pub_file)
            if pub_file.filename and not is_valid:
                return jsonify({'error': f'Publications file error: {message}'}), 400
            if pub_file.filename and is_valid:
                try:
                    uploaded_files_text['publications'] = process_uploaded_file(pub_file)
                    logger.info(f"Publications file processed: {pub_file.filename}")
                except Exception as e:
                    return jsonify({'error': f'Error processing publications file: {str(e)}'}), 400
        
        # Handle form data
        form_data = request.form.to_dict()
        session_id = get_session_id()
        
        logger.info(f"Faculty promotion letter API called - Session: {session_id}")
        
        # TODO: Implement Claude API call with form_data and uploaded_files_text
        # This is where you'll add the specific Claude prompt and logic
        
        return jsonify({
            'success': True,
            'message': 'Faculty promotion letter endpoint ready',
            'session_id': session_id,
            'files_processed': list(uploaded_files_text.keys()),
            'form_data_received': list(form_data.keys())
        })
    
    except Exception as e:
        logger.error(f"Error in faculty promotion letter API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Personal Statement
@app.route('/personal-statement')
def personal_statement():
    session_id = get_session_id()
    logger.info(f"Personal statement page accessed - Session: {session_id}")
    return render_template('personal_statement.html')

@app.route('/api/personal-statement', methods=['POST'])
@limiter.limit("5 per minute")
def api_personal_statement():
    if not claude_client:
        return jsonify({'error': 'Claude API not available'}), 503
    
    try:
        # Handle file uploads
        uploaded_files_text = {}
        
        # Process CV upload
        if 'cv_file' in request.files:
            cv_file = request.files['cv_file']
            is_valid, message = validate_file(cv_file)
            if cv_file.filename and not is_valid:
                return jsonify({'error': f'CV file error: {message}'}), 400
            if cv_file.filename and is_valid:
                try:
                    uploaded_files_text['cv'] = process_uploaded_file(cv_file)
                    logger.info(f"CV file processed: {cv_file.filename}")
                except Exception as e:
                    return jsonify({'error': f'Error processing CV file: {str(e)}'}), 400
        
        # Process job posting/requirements upload
        if 'job_file' in request.files:
            job_file = request.files['job_file']
            is_valid, message = validate_file(job_file)
            if job_file.filename and not is_valid:
                return jsonify({'error': f'Job posting file error: {message}'}), 400
            if job_file.filename and is_valid:
                try:
                    uploaded_files_text['job_posting'] = process_uploaded_file(job_file)
                    logger.info(f"Job posting file processed: {job_file.filename}")
                except Exception as e:
                    return jsonify({'error': f'Error processing job posting file: {str(e)}'}), 400
        
        # Handle form data
        form_data = request.form.to_dict()
        session_id = get_session_id()
        
        logger.info(f"Personal statement API called - Session: {session_id}")
        
        # TODO: Implement Claude API call with form_data and uploaded_files_text
        # This is where you'll add the specific Claude prompt and logic
        
        return jsonify({
            'success': True,
            'message': 'Personal statement endpoint ready',
            'session_id': session_id,
            'files_processed': list(uploaded_files_text.keys()),
            'form_data_received': list(form_data.keys())
        })
    
    except Exception as e:
        logger.error(f"Error in personal statement API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
