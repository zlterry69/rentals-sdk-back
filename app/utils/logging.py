"""
Logging configuration
"""
import structlog
import logging
import sys
from app.config import settings


def setup_logging():
    """Setup structured logging configuration"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG)  # Changed to DEBUG
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Always use ConsoleRenderer for debugging
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_request_logger():
    """Get a logger for request handling"""
    return structlog.get_logger("request")