from flask import Flask, render_template, request, jsonify, session
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

# Simple configuration without external dependencies
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
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

# Initialize simple rate limiter (memory-based)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)
logger.info("Rate limiter initialized with memory storage")

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

def build_claude_prompt(form_data, uploaded_files_text):
    """Build Claude prompt from form data and uploaded files"""
    
    # Get the custom prompt from the form
    custom_prompt = form_data.get('claude_prompt', '').strip()
    if not custom_prompt:
        return None, "No Claude prompt provided"
    
    # Build the context sections
    context_sections = []
    
    # Add form data (excluding the prompt itself)
    form_context = {}
    for key, value in form_data.items():
        if key != 'claude_prompt' and value.strip():
            form_context[key] = value.strip()
    
    if form_context:
        context_sections.append("=== FORM DATA ===")
        for key, value in form_context.items():
            context_sections.append(f"{key.replace('_', ' ').title()}: {value}")
    
    # Add file contents
    if uploaded_files_text:
        for file_type, content in uploaded_files_text.items():
            if content.strip():
                context_sections.append(f"\n=== {file_type.upper()} FILE CONTENT ===")
                context_sections.append(content.strip())
    
    # Combine everything
    if context_sections:
        full_prompt = "\n".join(context_sections) + "\n\n" + custom_prompt
    else:
        full_prompt = custom_prompt
    
    return full_prompt, None

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

# Generic page route
@app.route('/<page_name>')
def generic_page(page_name):
    """Serve any page that has a corresponding template"""
    session_id = get_session_id()
    logger.info(f"Page accessed: {page_name} - Session: {session_id}")
    
    # Convert URL format to template format (e.g., chairs-promotion-letter -> chairs_promotion_letter.html)
    template_name = page_name.replace('-', '_') + '.html'
    
    try:
        return render_template(template_name, page_name=page_name)
    except Exception as e:
        logger.error(f"Template not found: {template_name} - {e}")
        return render_template('404.html'), 404

# Generic API endpoint
@app.route('/api/<page_name>', methods=['POST'])
@limiter.limit("5 per minute")
def generic_api(page_name):
    """Generic API endpoint that handles any page"""
    if not claude_client:
        return jsonify({'error': 'Claude API not available'}), 503
    
    try:
        # Handle file uploads - process all uploaded files
        uploaded_files_text = {}
        
        for field_name in request.files:
            file = request.files[field_name]
            if file and file.filename:
                is_valid, message = validate_file(file)
                if not is_valid:
                    return jsonify({'error': f'{field_name} error: {message}'}), 400
                
                try:
                    extracted_text = process_uploaded_file(file)
                    if extracted_text:
                        # Clean up field name for context
                        clean_field_name = field_name.replace('_file', '').replace('_', ' ')
                        uploaded_files_text[clean_field_name] = extracted_text
                        logger.info(f"File processed: {file.filename} for field {field_name}")
                except Exception as e:
                    return jsonify({'error': f'Error processing {field_name}: {str(e)}'}), 400
        
        # Handle form data
        form_data = request.form.to_dict()
        session_id = get_session_id()
        
        logger.info(f"API called for page: {page_name} - Session: {session_id}")
        
        # Build Claude prompt from form data and files
        claude_prompt, error = build_claude_prompt(form_data, uploaded_files_text)
        if error:
            return jsonify({'error': error}), 400
        
        # Call Claude API
        try:
            message = claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": claude_prompt}
                ]
            )
            
            generated_content = message.content[0].text
            
            logger.info(f"Claude API successful for page: {page_name} - Session: {session_id}")
            
            return jsonify({
                'success': True,
                'content': generated_content,
                'session_id': session_id,
                'files_processed': list(uploaded_files_text.keys()),
                'form_fields_received': [k for k in form_data.keys() if k != 'claude_prompt']
            })
            
        except Exception as e:
            logger.error(f"Claude API error for page {page_name}: {e}")
            return jsonify({'error': f'Error generating content: {str(e)}'}), 500
    
    except Exception as e:
        logger.error(f"Error in API for page {page_name}: {e}")
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
