from doctest import debug
import logging
import sys
import os
from typing import Dict, Any

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    Set up standardized logger with both file and console handlers
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    # Create or get logger
    logger = logging.getLogger(name)
    
    # Avoid reconfiguring existing logger
    if logger.handlers:
        return logger
    
    # Set level based on environment or configuration
    log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Make propagation configurable
    propagate_logs = os.getenv('PROPAGATE_LOGS', 'False').lower() == 'true'
    logger.propagate = propagate_logs
    
    # Add handlers (example for file and console)
    # [Handler configuration would go here]
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # Create file handler with UTF-8 encoding
    file_handler = logging.FileHandler('app.log', encoding='utf-8')
    file_handler.setFormatter(file_formatter)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger