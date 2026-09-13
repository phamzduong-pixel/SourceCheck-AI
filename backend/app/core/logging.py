"""Structured logging setup for SourceCheck AI."""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root application logger."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("sourcecheck")
    return logger


logger = setup_logging()
