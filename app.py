"""
Main Flask application - routes and error handlers only
"""

from flask import render_template, request, jsonify, session
from datetime import datetime
import os

# Import our modular components
from config import create_app, setup_logging, setup_rate_limiter, setup_claude_client, ensure_directories
from file_processors import process_uploaded_file, validate_file, load_server_files
from page_handlers import handle_no_call_page, handle_claude_call_page
from utils import get_session_id, get_server_files_info

# Initialize application components
app = create_app()
logger = setup_logging()
limiter = setup_rate_limiter(app)
claude_client = setup_claude_client()

# Ensure required directories exist
ensure_directories()

# Log initialization status
if claude_client:
    logger.info("Application initialized successfully with Claude API")
else:
    logger.warning("Application initialized without Claude API")

# Routes
@app.route('/')
def home():
    session_id = get_session_id()
    logger.info(f"Home page accessed - Session: {session_id}")
    return render_template('home.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'claude_available': claude_client is not None
    })

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content response

@app.route('/<page_name>')
def generic_page(page_name):
    """Serve any page that has a corresponding template"""
    session_id = get_session_id()
    logger.info(f"Page accessed: {page_name} - Session: {session_id}")
    
    # Convert URL format to template format (e.g., chairs-promotion-letter -> chairs_promotion_letter.html)
    template_name = page_name.replace('-', '_') + '.html'
    
    # Load server files for this page to show on the page
    try:
        server_files_info = get_server_files_info(page_name)
        logger.info(f"Server files info loaded for {page_name}: {len(server_files_info)} files")
    except Exception as e:
        logger.error(f"Error loading server files info for {page_name}: {e}")
        server_files_info = []
    
    try:
        return render_template(template_name, page_name=page_name, server_files_info=server_files_info)
    except Exception as e:
        logger.error(f"Template error for {template_name}: {e}")
        return render_template('404.html'), 404

@app.route('/api/<page_name>', methods=['POST'])
@limiter.limit("5 per minute")
def generic_api(page_name):
    """Generic API endpoint that handles any page"""
    try:
        # Handle file uploads - process all uploaded files
        uploaded_files_data = {}
        
        for field_name in request.files:
            file = request.files[field_name]
            if file and file.filename:
                is_valid, message = validate_file(file)
                if not is_valid:
                    return jsonify({'error': f'{field_name} error: {message}'}), 400
                
                try:
                    file_data = process_uploaded_file(file)
                    if file_data:
                        # Clean up field name for context
                        clean_field_name = field_name.replace('_file', '').replace('_', ' ')
                        uploaded_files_data[clean_field_name] = file_data
                        logger.info(f"File processed: {file.filename} for field {field_name}")
                except Exception as e:
                    return jsonify({'error': f'Error processing {field_name}: {str(e)}'}), 400
        
        # Load server files for this page
        server_files_data = load_server_files(page_name)
        
        # Handle form data
        form_data = request.form.to_dict()
        session_id = get_session_id()
        
        logger.info(f"API called for page: {page_name} - Session: {session_id}")
        
        # Check page type based on form data
        page_type = form_data.get('page_type', 'claude-call')
        
        if page_type == 'no-call':
            # Handle no-call pages (no Claude API, just return organized data)
            return handle_no_call_page(page_name, form_data, uploaded_files_data, server_files_data, session_id)
        elif page_type == 'claude-call':
            # Handle Claude API pages (existing functionality)
            return handle_claude_call_page(page_name, form_data, uploaded_files_data, server_files_data, session_id, claude_client)
        else:
            return jsonify({'error': f'Unknown page type: {page_type}'}), 400
    
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
    try:
        return render_template('404.html'), 404
    except:
        # Fallback if 404.html template fails
        return '''
        <html><body>
        <h1>404 Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <a href="/">Go Home</a>
        </body></html>
        ''', 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    try:
        return render_template('500.html'), 500
    except:
        # Fallback if 500.html template fails
        return '''
        <html><body>
        <h1>500 Internal Server Error</h1>
        <p>The server encountered an internal error.</p>
        <a href="/">Go Home</a>
        </body></html>
        ''', 500

if __name__ == '__main__':
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
