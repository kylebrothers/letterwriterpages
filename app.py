from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
import os
import logging
from datetime import datetime
import uuid

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = None  # Will be set up with Redis connection
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'promotion-letters:'

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
        data = request.get_json()
        session_id = get_session_id()
        
        logger.info(f"Chairs promotion letter API called - Session: {session_id}")
        
        # Process the request with Claude
        # This is where you'll implement the specific logic for chairs promotion letters
        
        return jsonify({
            'success': True,
            'message': 'Chairs promotion letter endpoint ready',
            'session_id': session_id
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
        data = request.get_json()
        session_id = get_session_id()
        
        logger.info(f"Faculty promotion letter API called - Session: {session_id}")
        
        # Process the request with Claude
        # This is where you'll implement the specific logic for faculty promotion letters
        
        return jsonify({
            'success': True,
            'message': 'Faculty promotion letter endpoint ready',
            'session_id': session_id
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
        data = request.get_json()
        session_id = get_session_id()
        
        logger.info(f"Personal statement API called - Session: {session_id}")
        
        # Process the request with Claude
        # This is where you'll implement the specific logic for personal statements
        
        return jsonify({
            'success': True,
            'message': 'Personal statement endpoint ready',
            'session_id': session_id
        })
    
    except Exception as e:
        logger.error(f"Error in personal statement API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
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
