"""
BuildTrace Flask API Application
Lightweight API layer for async job processing
"""

import os
import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from flask import Flask, request, session, send_file, send_from_directory
from flask_cors import CORS
from config import config
import os

# Configure logging with timestamps
class TimestampFormatter(logging.Formatter):
    """Custom formatter that adds timestamps"""
    def format(self, record):
        record.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return super().format(record)

# Create formatter
formatter = TimestampFormatter(
    '%(timestamp)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Console handler (always enabled)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# File handler for local development (only if not in production)
if config.IS_DEVELOPMENT:
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Application log file
    app_log_file = logs_dir / 'app.log'
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # Keep 5 backup files
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Error log file (only errors and above)
    error_log_file = logs_dir / 'errors.log'
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

# Flask/Werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)
werkzeug_handler = logging.StreamHandler(sys.stdout)
werkzeug_handler.setFormatter(formatter)
werkzeug_logger.addHandler(werkzeug_handler)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
# Session configuration for OAuth
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allows cookies in cross-origin redirects
# In production (HTTPS), Secure must be True. In development (HTTP), it should be False
app.config['SESSION_COOKIE_SECURE'] = config.IS_PRODUCTION  # True in production (HTTPS), False in dev
app.config['SESSION_COOKIE_DOMAIN'] = None  # Don't set domain to allow cross-subdomain cookies

# Get allowed origins from config or environment
FRONTEND_URL = config.FRONTEND_URL or os.getenv('FRONTEND_URL', 'http://localhost:3000')

# CORS allowed origins - can be set via environment variable or defaults
CORS_ALLOWED_ORIGINS_ENV = os.getenv('CORS_ALLOWED_ORIGINS', '')
if CORS_ALLOWED_ORIGINS_ENV:
    # Parse from comma-separated environment variable
    ALLOWED_ORIGINS = [
        origin.strip() for origin in CORS_ALLOWED_ORIGINS_ENV.split(",") 
        if origin.strip()
    ]
else:
    # Default origins (fallback if env var not set)
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        FRONTEND_URL,
        "https://buildtrace-frontend-otllaxbiza-wl.a.run.app",
        "https://buildtrace-frontend-136394139608.us-west2.run.app"
    ]

# Remove duplicates while preserving order
ALLOWED_ORIGINS = list(dict.fromkeys(ALLOWED_ORIGINS))
logger.info(f"CORS configured for origins: {ALLOWED_ORIGINS}")
logger.info(f"Frontend URL: {FRONTEND_URL}")

# Enable CORS for frontend - Flask-CORS handles OPTIONS automatically
CORS(
    app,
    origins=ALLOWED_ORIGINS,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Type"],
    supports_credentials=True,
    automatic_options=True,
)

# Add request logging middleware
@app.before_request
def log_request_info():
    """Log all incoming requests"""
    logger.debug(f"Request: {request.method} {request.path}")
    logger.debug(f"Headers: {dict(request.headers)}")
    if request.method == 'OPTIONS':
        logger.debug("OPTIONS preflight request detected")

@app.after_request
def log_response_info(response):
    """Log all outgoing responses and enforce CORS headers for allowed origins."""
    logger.debug(f"Response: {response.status_code} for {request.method} {request.path}")
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.setdefault('Vary', 'Origin')
    if request.method == 'OPTIONS':
        requested_headers = request.headers.get('Access-Control-Request-Headers', '')
        allow_headers = {'Authorization', 'Content-Type', 'X-Requested-With'}
        if requested_headers:
            allow_headers.update({h.strip() for h in requested_headers.split(',') if h.strip()})
        response.headers['Access-Control-Allow-Headers'] = ', '.join(sorted(allow_headers))
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response.headers['Access-Control-Max-Age'] = '3600'
    return response

# Initialize database (lazy - only when needed)
# Database will be initialized when first accessed if USE_DATABASE is True
if config.USE_DATABASE:
    logger.info("Database enabled (will initialize on first use)")
    # init_db()  # Uncomment to create tables on startup

    # Run migrations on startup
    try:
        from run_migrations import run_migrations
        logger.info("Running database migrations...")
        run_migrations()
        logger.info("✓ Migrations completed")
    except Exception as e:
        logger.warning(f"Could not run migrations: {e}")
        logger.warning("App will continue, but some features may not work correctly")

# Register blueprints (they will handle database errors gracefully)
try:
    from blueprints.jobs import jobs_bp
    from blueprints.drawings import drawings_bp
    from blueprints.projects import projects_bp, documents_bp
    from blueprints.overlays import overlays_bp
    from blueprints.summaries import summaries_bp
    app.register_blueprint(jobs_bp)
    app.register_blueprint(drawings_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(overlays_bp)
    app.register_blueprint(summaries_bp)
    logger.info("Core blueprints registered successfully")
except Exception as e:
    logger.error(f"Could not register core blueprints: {e}", exc_info=True)
    logger.warning("App will run with limited functionality.")

# Register session-based blueprints (for backward compatibility)
try:
    from blueprints.sessions import sessions_bp
    from blueprints.chat import chat_bp
    app.register_blueprint(sessions_bp)
    app.register_blueprint(chat_bp)
    logger.info("Session-based blueprints registered successfully")
except Exception as e:
    logger.warning(f"Could not register session-based blueprints: {e}")
    logger.info("Session-based features will not be available")

# Register auth blueprint (optional - only if OAuth is configured)
try:
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("Auth blueprint registered successfully")
except Exception as e:
    logger.warning(f"Could not register auth blueprint: {e}")
    logger.info("Auth features will not be available")

# Log all registered routes for debugging
try:
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append(f"  {rule.rule} -> {rule.endpoint} {list(rule.methods)}")
    logger.debug(f"Registered routes:\n" + "\n".join(routes))
except Exception as e:
    logger.debug(f"Could not list routes: {e}")

# File serving endpoint for local development
@app.route('/api/v1/files/<path:file_path>', methods=['GET'])
def serve_file(file_path: str):
    """Serve files from local storage in development mode"""
    try:
        from config import config
        from gcp.storage.storage_service import StorageService
        
        storage = StorageService()
        if storage.use_gcs:
            # In production with GCS, this shouldn't be called
            return {'error': 'File serving not available in GCS mode'}, 404
        
        # Get local file path
        local_path = storage._get_local_path(file_path)
        
        if not os.path.exists(local_path):
            return {'error': 'File not found'}, 404
        
        # Determine content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(local_path)
        if not content_type:
            content_type = 'application/octet-stream'
        
        return send_file(local_path, mimetype=content_type)
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {e}", exc_info=True)
        return {'error': str(e)}, 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'environment': config.ENVIRONMENT,
        'database': 'enabled' if config.USE_DATABASE else 'disabled',
        'gcs': 'enabled' if config.USE_GCS else 'disabled',
        'pubsub': 'enabled' if config.USE_PUBSUB else 'disabled',
        'oauth': 'enabled' if config.GOOGLE_CLIENT_ID else 'disabled'
    }, 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return {
        'name': 'BuildTrace API',
        'version': '2.0.0',
        'status': 'running'
    }, 200

if __name__ == '__main__':
    logger.info(f"Starting BuildTrace API in {config.ENVIRONMENT} mode")
    logger.info(f"Features: DB={config.USE_DATABASE}, GCS={config.USE_GCS}, PubSub={config.USE_PUBSUB}")
    if config.IS_DEVELOPMENT:
        logs_dir = Path('logs')
        logger.info(f"Logs will be saved to: {logs_dir.absolute()}/")
        logger.info(f"  - Application logs: {logs_dir / 'app.log'}")
        logger.info(f"  - Error logs: {logs_dir / 'errors.log'}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
