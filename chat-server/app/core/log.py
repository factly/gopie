import logging
import sys

from app.core.config import settings

logger = logging.getLogger("app")


def setup_logger():
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stdout,
        format="[%(levelname)s] %(message)s",
    )

    if settings.MODE == "development":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
