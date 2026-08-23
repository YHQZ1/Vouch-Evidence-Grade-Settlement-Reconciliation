"""Logging setup for the Vouch backend."""

import logging

APPLICATION_LOGGER_NAME = "app"
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(log_level: str) -> logging.Logger:
    """Configure and return the consistent application logger.

    The named ``app`` logger is the parent of all application modules. A single
    handler is installed on first use, making repeated application construction
    safe and free of duplicate log lines.
    """
    logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    logger.setLevel(log_level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)

    return logger
