"""
BuildTrace Flask API Application
Lightweight API layer for async job processing
"""

import os
import logging
import sys
from datetime import datetime
from flask import Flask, request, session
from flask_cors import CORS
from config import config

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

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

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
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    FRONTEND_URL,
    "https://buildtrace-frontend-otllaxbiza-wl.a.run.app",
    "https://buildtrace-frontend-136394139608.us-west2.run.app"
]
# Remove duplicates while preserving order
ALLOWED_ORIGINS = list(dict.fromkeys(ALLOWED_ORIGINS))

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
    return response

# Initialize database (lazy - only when needed)
# Database will be initialized when first accessed if USE_DATABASE is True
if config.USE_DATABASE:
    logger.info("Database enabled (will initialize on first use)")
    # init_db()  # Uncomment to create tables on startup

# Register blueprints (they will handle database errors gracefully)
try:
    from blueprints.jobs import jobs_bp
    from blueprints.drawings import drawings_bp
    from blueprints.projects import projects_bp
    from blueprints.overlays import overlays_bp
    from blueprints.summaries import summaries_bp
    app.register_blueprint(jobs_bp)
    app.register_blueprint(drawings_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(overlays_bp)
    app.register_blueprint(summaries_bp)
    logger.info("Core blueprints registered successfully")
except Exception as e:
    logger.error(f"Could not register core blueprints: {e}", exc_info=True)
    logger.warning("App will run with limited functionality.")

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
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
