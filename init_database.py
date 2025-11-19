#!/usr/bin/env python3
"""
Initialize database schema
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import config
from src.logging_config import get_logger
from src.database import init_db

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    
    try:
        init_db()
        logger.info("✅ Database initialized successfully!")
        logger.info(f"Created tables: jobs, event_logs, system_metrics")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
