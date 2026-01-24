"""Centralized logging configuration for the backend."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    logger_name: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Name for the logger (defaults to root logger)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    if not logger.handlers:
        logger.addHandler(handler)

    logger.propagate = False

    return logger
