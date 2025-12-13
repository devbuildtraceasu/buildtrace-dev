import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)

# Try to import psycopg2, but don't fail if it's not available
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not available. Database features will be disabled.")

class DatabaseConfig:
    """Database configuration and connection management"""

    def __init__(self):
        self.env = os.getenv('ENVIRONMENT', 'development')
        self.setup_database_url()

    def setup_database_url(self):
        """Setup database URL based on environment"""
        if self.env == 'production':
            # Production: Use Cloud SQL with Unix socket
            self.database_url = self._get_cloud_sql_url()
        elif self.env == 'staging':
            # Staging: Use Cloud SQL with Cloud SQL Proxy
            self.database_url = self._get_cloud_sql_proxy_url()
        else:
            # Development: Use local PostgreSQL or Cloud SQL Proxy
            self.database_url = self._get_local_database_url()

    def _get_cloud_sql_url(self):
        """Get Cloud SQL connection string for production"""
        db_user = os.getenv('DB_USER', 'buildtrace_user')
        db_pass = os.getenv('DB_PASS')
        db_name = os.getenv('DB_NAME', 'buildtrace_db')
        instance_connection_name = os.getenv('INSTANCE_CONNECTION_NAME', 'buildtrace-dev:us-west2:buildtrace-dev-db')

        if os.getenv('USE_CLOUD_SQL_AUTH_PROXY'):
            # If using Cloud SQL Proxy
            return f"postgresql://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}"
        else:
            # Direct connection via Unix socket (Cloud Run)
            logger.info(f"Using Unix socket connection for Cloud Run")
            return f"postgresql://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{instance_connection_name}"

    def _get_cloud_sql_proxy_url(self):
        """Get Cloud SQL Proxy connection string"""
        db_user = os.getenv('DB_USER', 'buildtrace_user')
        db_pass = os.getenv('DB_PASS')
        db_name = os.getenv('DB_NAME', 'buildtrace_db')
        return f"postgresql://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}"

    def _get_local_database_url(self):
        """Get local database connection string"""
        # Check if using Cloud SQL Proxy
        if os.getenv('USE_CLOUD_SQL_AUTH_PROXY', 'false').lower() == 'true':
            # Use Cloud SQL Proxy configuration
            db_user = os.getenv('DB_USER', 'buildtrace_user')
            db_pass = os.getenv('DB_PASS')
            db_name = os.getenv('DB_NAME', 'buildtrace_db')
            return f"postgresql://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}"
        else:
            # Use local PostgreSQL
            db_user = os.getenv('DB_USER', 'postgres')
            db_pass = os.getenv('DB_PASS', 'postgres')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'buildtrace_db')
            return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self.initialize()

    def initialize(self):
        """Initialize database engine and session factory"""
        try:
            # Check if psycopg2 is available
            if not PSYCOPG2_AVAILABLE:
                logger.warning("psycopg2 not available. Database features disabled.")
                self.engine = None
                self.SessionLocal = None
                return
            
            # Check if database URL is configured
            if not self.config.database_url:
                logger.warning("Database URL not configured, skipping initialization")
                self.engine = None
                self.SessionLocal = None
                return
            
            # Create engine with appropriate configuration
            if self.config.env == 'production':
                # Production: Use connection pooling
                self.engine = create_engine(
                    self.config.database_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    echo=False
                )
            else:
                # Development: Simpler configuration
                self.engine = create_engine(
                    self.config.database_url,
                    echo=True if self.config.env == 'development' else False,
                    pool_pre_ping=True
                )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"Database connection initialized for {self.config.env} environment")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            # Don't raise in development - allow app to run without database
            if self.config.env == 'production':
                raise
            else:
                logger.warning("Continuing without database connection in development mode")
                self.engine = None
                self.SessionLocal = None

    def create_tables(self):
        """Create all tables in the database"""
        if not self.engine:
            raise RuntimeError("Database not initialized. Check your database configuration.")
        from gcp.database.models import Base
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def drop_tables(self):
        """Drop all tables in the database (use with caution!)"""
        from gcp.database.models import Base
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    @contextmanager
    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Check your database configuration.")
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def get_session_dependency(self):
        """Dependency for FastAPI/Flask to get database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


# Global database manager instance (lazy initialization)
_db_manager = None

def _get_db_manager():
    """Get or create database manager instance (lazy initialization)"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# Helper functions for Flask app
def get_db():
    """Get database session for Flask routes"""
    manager = _get_db_manager()
    if not manager.SessionLocal:
        raise RuntimeError("Database not initialized. Set USE_DATABASE=true and configure database connection.")
    return manager.SessionLocal()


def init_db():
    """Initialize database tables"""
    _get_db_manager().create_tables()


@contextmanager
def get_db_session():
    """Context manager for database operations in Flask"""
    session = get_db()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

