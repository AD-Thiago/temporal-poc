"""
Structured logging configuration with Cloud Logging integration
"""
import logging
import sys
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
import google.cloud.logging as cloud_logging
from .config import config


class StructuredLogger:
    """Structured logger with Cloud Logging support"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._configure_logger()
    
    def _configure_logger(self):
        """Configure logger with JSON formatter and Cloud Logging"""
        self.logger.setLevel(getattr(logging, config.logging.level))
        
        # Remove existing handlers
        self.logger.handlers = []
        
        if config.logging.enable_cloud_logging:
            # Google Cloud Logging integration
            try:
                client = cloud_logging.Client()
                client.setup_logging()
            except Exception as e:
                print(f"Warning: Could not setup Cloud Logging: {e}", file=sys.stderr)
        
        # Console handler with JSON format
        console_handler = logging.StreamHandler(sys.stdout)
        
        if config.logging.format == 'json':
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _add_context(self, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add default context to log entries"""
        context = {
            'service': config.logging.service_name,
            'environment': config.logging.environment,
        }
        if extra:
            context.update(extra)
        return context
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self.logger.info(message, extra=self._add_context(kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self.logger.warning(message, extra=self._add_context(kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self.logger.error(message, extra=self._add_context(kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self.logger.debug(message, extra=self._add_context(kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self.logger.critical(message, extra=self._add_context(kwargs))


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
