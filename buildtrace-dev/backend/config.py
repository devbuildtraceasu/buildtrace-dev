"""
BuildTrace Configuration Management
Handles environment-based configuration for local and cloud deployments
"""

import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Central configuration for BuildTrace application"""

    def __init__(self):
        # Load environment variables
        self._load_environment()

        # Core environment settings
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.IS_PRODUCTION = self.ENVIRONMENT == 'production'
        self.IS_DEVELOPMENT = self.ENVIRONMENT == 'development'

        # Feature flags
        self.USE_DATABASE = os.getenv('USE_DATABASE', 'true' if self.IS_PRODUCTION else 'false').lower() == 'true'
        self.USE_GCS = os.getenv('USE_GCS', 'true' if self.IS_PRODUCTION else 'false').lower() == 'true'
        self.USE_ASYNC_PROCESSING = os.getenv('USE_ASYNC_PROCESSING', 'true').lower() == 'true'
        self.USE_PUBSUB = os.getenv('USE_PUBSUB', 'true' if self.IS_PRODUCTION else 'false').lower() == 'true'
        self.USE_FIREBASE_AUTH = os.getenv('USE_FIREBASE_AUTH', 'false').lower() == 'true'

        # OAuth 2.0 settings (Google Cloud Identity)
        self.GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
        self.GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
        self.GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 
            'http://localhost:5001/api/v1/auth/google/callback' if self.IS_DEVELOPMENT 
            else 'https://yourdomain.com/api/v1/auth/google/callback')
        # Frontend URL for OAuth redirects after callback
        self.FRONTEND_URL = os.getenv('FRONTEND_URL',
            'http://localhost:3000' if self.IS_DEVELOPMENT
            else 'https://yourdomain.com')
        allowed_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '')
        self.ALLOWED_EMAIL_DOMAINS = [d.strip() for d in allowed_domains.split(',') if d.strip()] if allowed_domains else []

        # Application settings
        self.APP_NAME = os.getenv('APP_NAME', 'BuildTrace')
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        self.DEBUG = os.getenv('DEBUG', 'true' if self.IS_DEVELOPMENT else 'false').lower() == 'true'

        # Server settings
        self.HOST = os.getenv('HOST', '0.0.0.0')
        self.PORT = int(os.getenv('PORT', '8080' if self.IS_PRODUCTION else '5001'))

        # Database settings (only used if USE_DATABASE is True)
        if self.USE_DATABASE:
            self.DB_USER = os.getenv('DB_USER', 'buildtrace_user')
            self.DB_PASS = os.getenv('DB_PASS', '')
            self.DB_NAME = os.getenv('DB_NAME', 'buildtrace_db')
            self.INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME', '')

            # Build database URL (URL-encode password to handle special characters)
            encoded_password = quote_plus(self.DB_PASS) if self.DB_PASS else ''
            if self.IS_PRODUCTION and self.INSTANCE_CONNECTION_NAME:
                # Cloud SQL via Unix socket
                self.DATABASE_URL = f"postgresql://{self.DB_USER}:{encoded_password}@/{self.DB_NAME}?host=/cloudsql/{self.INSTANCE_CONNECTION_NAME}"
            else:
                # Local PostgreSQL
                self.DB_HOST = os.getenv('DB_HOST', 'localhost')
                self.DB_PORT = os.getenv('DB_PORT', '5432')
                self.DATABASE_URL = f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        else:
            self.DATABASE_URL = None

        # Storage settings
        if self.USE_GCS:
            self.GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'buildtrace-dev-input-buildtrace-dev')
            self.GCS_UPLOAD_BUCKET = os.getenv('GCS_UPLOAD_BUCKET', 'buildtrace-drawings-upload')
            self.GCS_PROCESSED_BUCKET = os.getenv('GCS_PROCESSED_BUCKET', 'buildtrace-drawings-processed')
        else:
            # Local storage paths
            self.LOCAL_UPLOAD_PATH = os.getenv('LOCAL_UPLOAD_PATH', 'uploads')
            self.LOCAL_RESULTS_PATH = os.getenv('LOCAL_RESULTS_PATH', 'results')
            self.LOCAL_TEMP_PATH = os.getenv('LOCAL_TEMP_PATH', 'temp')
            self.LOCAL_OUTPUT_PATH = os.getenv('LOCAL_OUTPUT_PATH', 'outputs')  # For dev mode outputs
            self.GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', '')
            self.GCS_UPLOAD_BUCKET = os.getenv('GCS_UPLOAD_BUCKET', '')
            self.GCS_PROCESSED_BUCKET = os.getenv('GCS_PROCESSED_BUCKET', '')

        # Processing settings
        self.MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(70 * 1024 * 1024)))  # 70MB default
        self.PROCESSING_TIMEOUT = int(os.getenv('PROCESSING_TIMEOUT', '3600'))  # 1 hour default
        self.DEFAULT_DPI = int(os.getenv('DEFAULT_DPI', '300'))
        self.MAX_SYNC_PAGES = int(os.getenv('MAX_SYNC_PAGES', '10'))
        self.MEMORY_LIMIT_GB = float(os.getenv('MEMORY_LIMIT_GB', '25.0' if self.IS_PRODUCTION else '10.0'))

        # OpenAI settings
        # IMPORTANT: Set OPENAI_API_KEY as environment variable for security
        # Do not hardcode API keys in source code
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
        # Use GPT-5 as default model
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5')
        self.USE_AI_ANALYSIS = os.getenv('USE_AI_ANALYSIS', 'true').lower() == 'true'
        
        # Gemini settings (for chatbot)
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
        # Model options: 'models/gemini-2.5-pro' (best quality), 'models/gemini-2.5-flash' (faster)
        self.GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'models/gemini-2.5-pro')
        
        # Warn if API key is not set
        if not self.OPENAI_API_KEY and self.USE_AI_ANALYSIS:
            logger.warning("OPENAI_API_KEY not set - AI analysis features will be disabled")
        if not self.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set - chatbot features will be disabled")

        # Pub/Sub settings
        if self.USE_PUBSUB:
            self.GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', os.getenv('GOOGLE_CLOUD_PROJECT', 'buildtrace-dev'))
            self.PUBSUB_OCR_TOPIC = os.getenv('PUBSUB_OCR_TOPIC', 'buildtrace-dev-ocr-queue')
            self.PUBSUB_DIFF_TOPIC = os.getenv('PUBSUB_DIFF_TOPIC', 'buildtrace-dev-diff-queue')
            self.PUBSUB_SUMMARY_TOPIC = os.getenv('PUBSUB_SUMMARY_TOPIC', 'buildtrace-dev-summary-queue')
            self.PUBSUB_OCR_SUBSCRIPTION = os.getenv('PUBSUB_OCR_SUBSCRIPTION', 'buildtrace-dev-ocr-worker-sub')
            self.PUBSUB_DIFF_SUBSCRIPTION = os.getenv('PUBSUB_DIFF_SUBSCRIPTION', 'buildtrace-dev-diff-worker-sub')
            self.PUBSUB_SUMMARY_SUBSCRIPTION = os.getenv('PUBSUB_SUMMARY_SUBSCRIPTION', 'buildtrace-dev-summary-worker-sub')

        # Security settings
        self.ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'png', 'jpg', 'jpeg'}
        self.MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '70'))

        # Session settings
        self.SESSION_LIFETIME_HOURS = int(os.getenv('SESSION_LIFETIME_HOURS', '24'))
        self.CLEANUP_OLD_SESSIONS = os.getenv('CLEANUP_OLD_SESSIONS', 'true').lower() == 'true'

    def _load_environment(self):
        """Load environment variables from appropriate .env file"""
        env = os.getenv('ENVIRONMENT', 'development')

        # Try to load environment-specific file first
        env_file = f'.env.{env}'
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
        elif os.path.exists('.env'):
            # Fallback to generic .env file
            load_dotenv('.env', override=True)

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration based on mode"""
        if self.USE_GCS:
            return {
                'type': 'gcs',
                'bucket_name': self.GCS_BUCKET_NAME,
                'upload_bucket': self.GCS_UPLOAD_BUCKET,
                'processed_bucket': self.GCS_PROCESSED_BUCKET
            }
        else:
            return {
                'type': 'local',
                'upload_path': self.LOCAL_UPLOAD_PATH,
                'results_path': self.LOCAL_RESULTS_PATH,
                'temp_path': self.LOCAL_TEMP_PATH
            }

    def get_data_config(self) -> Dict[str, Any]:
        """Get data persistence configuration"""
        if self.USE_DATABASE:
            return {
                'type': 'database',
                'url': self.DATABASE_URL
            }
        else:
            return {
                'type': 'file',
                'data_dir': os.getenv('LOCAL_DATA_DIR', 'data')
            }

    def validate(self) -> bool:
        """Validate configuration settings"""
        errors = []

        # Check required settings for cloud mode
        if self.IS_PRODUCTION:
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required in production")
            if self.USE_DATABASE and not self.DB_PASS:
                errors.append("DB_PASS is required when using database")
            if self.USE_GCS and not self.GCS_BUCKET_NAME:
                errors.append("GCS_BUCKET_NAME is required when using GCS")
            if self.USE_PUBSUB and not self.GCP_PROJECT_ID:
                errors.append("GCP_PROJECT_ID is required when using Pub/Sub")

        # Check for conflicts
        if self.USE_ASYNC_PROCESSING and not self.USE_DATABASE:
            errors.append("Async processing requires database to be enabled")

        if errors:
            for error in errors:
                logger.error(f"Configuration Error: {error}")
            return False

        return True

    def __repr__(self):
        return f"<Config env={self.ENVIRONMENT} db={self.USE_DATABASE} gcs={self.USE_GCS} pubsub={self.USE_PUBSUB}>"


# Global config instance
config = Config()

# Validate on import (only in production)
if config.IS_PRODUCTION and not config.validate():
    raise RuntimeError("Invalid configuration for production environment")
