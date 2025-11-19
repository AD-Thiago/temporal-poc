"""
Database connection management with Cloud SQL Connector
"""
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool
from google.cloud.sql.connector import Connector
import pg8000

from .config import config
from .logging_config import get_logger

logger = get_logger(__name__)

# SQLAlchemy base for models
Base = declarative_base()

# Global engine and session factory
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_connection():
    """Create a database connection using Cloud SQL Connector"""
    connector = Connector()
    
    conn = connector.connect(
        config.database.instance_connection_name,
        "pg8000",
        user=config.database.user,
        password=config.database.password,
        db=config.database.database_name
    )
    return conn


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine with Cloud SQL Connector"""
    global _engine
    
    if _engine is None:
        logger.info(
            "Creating database engine",
            instance=config.database.instance_connection_name,
            database=config.database.database_name
        )
        
        _engine = create_engine(
            "postgresql+pg8000://",
            creator=get_connection,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_timeout=config.database.pool_timeout,
            pool_recycle=config.database.pool_recycle,
            pool_pre_ping=True,  # Enable connection health checks
            echo=config.debug  # Log SQL queries in debug mode
        )
        
        # Log slow queries
        @event.listens_for(_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
            conn.info.setdefault('query_start_time', []).append(None)
        
        @event.listens_for(_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
            import time
            total = time.time() - conn.info['query_start_time'].pop(-1)
            if total > 1.0:  # Log queries taking > 1 second
                logger.warning(
                    "Slow query detected",
                    duration_seconds=total,
                    query=statement[:200]
                )
        
        logger.info("Database engine created successfully")
    
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create session factory"""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("Session factory created")
    
    return _SessionLocal


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    
    Usage:
        with get_db_session() as session:
            result = session.query(Model).all()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(
            "Database transaction failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
    finally:
        session.close()


def init_db():
    """Initialize database tables (create all tables defined in models)"""
    engine = get_engine()
    logger.info("Initializing database tables")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def close_db_connections():
    """Close all database connections (call on shutdown)"""
    global _engine, _SessionLocal
    
    if _engine:
        logger.info("Closing database connections")
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("Database connections closed")
