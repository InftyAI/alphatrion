import logging
import os
import sys


def configure_logging():
    """Configure logging for the server with GraphQL debugging support."""
    log_level = os.getenv("ALPHATRION_LOG_LEVEL", "INFO").upper()

    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set uvicorn logger to INFO to avoid too much noise
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    logger.info("Set ALPHATRION_LOG_LEVEL=DEBUG to see detailed GraphQL queries")
