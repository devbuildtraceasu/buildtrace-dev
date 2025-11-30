"""
BuildTrace Configuration Management
Handles environment-based configuration for local and cloud deployments
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

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
        self.USE_ASYNC_PROCESSING = os.getenv('USE_ASYNC_PROCESSING', 'false').lower() == 'true'
        self.USE_BACKGROUND_PROCESSING = os.getenv('USE_BACKGROUND_PROCESSING', 'true').lower() == 'true'
        self.USE_FIREBASE_AUTH = os.getenv('USE_FIREBASE_AUTH', 'false').lower() == 'true'

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

            # Build database URL
            if self.IS_PRODUCTION and self.INSTANCE_CONNECTION_NAME:
                # Cloud SQL via Unix socket
                self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASS}@/{self.DB_NAME}?host=/cloudsql/{self.INSTANCE_CONNECTION_NAME}"
            else:
                # Local PostgreSQL
                self.DB_HOST = os.getenv('DB_HOST', 'localhost')
                self.DB_PORT = os.getenv('DB_PORT', '5432')
                self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        else:
            self.DATABASE_URL = None

        # Storage settings
        if self.USE_GCS:
            self.GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'buildtrace-storage')
            self.GCS_UPLOAD_BUCKET = os.getenv('GCS_UPLOAD_BUCKET', 'buildtrace-drawings-upload')
            self.GCS_PROCESSED_BUCKET = os.getenv('GCS_PROCESSED_BUCKET', 'buildtrace-drawings-processed')
        else:
            # Local storage paths
            self.LOCAL_UPLOAD_PATH = os.getenv('LOCAL_UPLOAD_PATH', 'uploads')
            self.LOCAL_RESULTS_PATH = os.getenv('LOCAL_RESULTS_PATH', 'results')
            self.LOCAL_TEMP_PATH = os.getenv('LOCAL_TEMP_PATH', 'temp')

        # Processing settings
        self.MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(70 * 1024 * 1024)))  # 70MB default
        self.PROCESSING_TIMEOUT = int(os.getenv('PROCESSING_TIMEOUT', '3600'))  # 1 hour default
        self.DEFAULT_DPI = int(os.getenv('DEFAULT_DPI', '300'))
        self.MAX_SYNC_PAGES = int(os.getenv('MAX_SYNC_PAGES', '10'))
        self.MEMORY_LIMIT_GB = float(os.getenv('MEMORY_LIMIT_GB', '25.0' if self.IS_PRODUCTION else '10.0'))

        # OpenAI settings
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.USE_AI_ANALYSIS = os.getenv('USE_AI_ANALYSIS', 'true').lower() == 'true'

        # Cloud Tasks settings (only for async processing)
        if self.USE_ASYNC_PROCESSING:
            self.CLOUD_TASKS_QUEUE = os.getenv('CLOUD_TASKS_QUEUE', 'buildtrace-processing-queue')
            self.CLOUD_TASKS_LOCATION = os.getenv('CLOUD_TASKS_LOCATION', 'us-central1')
            self.CLOUD_TASKS_PROJECT = os.getenv('CLOUD_TASKS_PROJECT', 'buildtrace')
            self.WORKER_URL = os.getenv('WORKER_URL', '')

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

        # Check for conflicts
        if self.USE_ASYNC_PROCESSING and not self.USE_DATABASE:
            errors.append("Async processing requires database to be enabled")

        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False

        return True

    def __repr__(self):
        return f"<Config env={self.ENVIRONMENT} db={self.USE_DATABASE} gcs={self.USE_GCS} async={self.USE_ASYNC_PROCESSING}>"


# Global config instance
config = Config()

# Validate on import (only in production)
if config.IS_PRODUCTION and not config.validate():
    raise RuntimeError("Invalid configuration for production environment")