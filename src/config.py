"""
Configuration management for CUIDA+Care Worker
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Cloud SQL PostgreSQL configuration"""
    instance_connection_name: str = os.getenv(
        'CLOUD_SQL_CONNECTION_NAME',
        'adc-agent:us-central1:cuida-care-db'
    )
    database_name: str = os.getenv('DB_NAME', 'cuida_care')
    user: str = os.getenv('DB_USER', 'app_user')
    password: str = os.getenv('DB_PASSWORD', 'CuidaCare2025!Secure')
    
    # Connection pool settings
    pool_size: int = int(os.getenv('DB_POOL_SIZE', '5'))
    max_overflow: int = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    pool_timeout: int = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    pool_recycle: int = int(os.getenv('DB_POOL_RECYCLE', '1800'))
    
    @property
    def connection_string(self) -> str:
        """PostgreSQL connection string for Cloud SQL Connector"""
        return f"postgresql+pg8000://{self.user}:{self.password}@/{self.database_name}?unix_sock=/cloudsql/{self.instance_connection_name}/.s.PGSQL.5432"


@dataclass
class PubSubConfig:
    """Pub/Sub configuration"""
    project_id: str = os.getenv('GCP_PROJECT_ID', 'adc-agent')
    topic_name: str = os.getenv('PUBSUB_TOPIC', 'hello-topic')
    dlq_topic_name: str = os.getenv('PUBSUB_DLQ_TOPIC', 'hello-topic-dlq')
    subscription_name: str = os.getenv('PUBSUB_SUBSCRIPTION', 'hello-sub')
    max_retry_attempts: int = int(os.getenv('PUBSUB_MAX_RETRIES', '3'))


@dataclass
class LoggingConfig:
    """Structured logging configuration"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    format: str = 'json'  # json or text
    enable_cloud_logging: bool = os.getenv('ENABLE_CLOUD_LOGGING', 'true').lower() == 'true'
    service_name: str = os.getenv('SERVICE_NAME', 'temporal-worker')
    environment: str = os.getenv('ENVIRONMENT', 'production')


@dataclass
class AppConfig:
    """Application configuration"""
    port: int = int(os.getenv('PORT', '8080'))
    debug: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    database: DatabaseConfig = None
    pubsub: PubSubConfig = None
    logging: LoggingConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.pubsub is None:
            self.pubsub = PubSubConfig()
        if self.logging is None:
            self.logging = LoggingConfig()


# Global config instance
config = AppConfig()
