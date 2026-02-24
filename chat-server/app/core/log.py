import logging
import sys

from app.core.config import settings

logger = logging.getLogger("app")


class CustomLogger:
    def __init__(self, base_logger, dev_mode: bool = False):
        self._logger = base_logger
        self.dev_mode = dev_mode

    def exception(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, stack_info=True, **kwargs)
        if self.dev_mode:
            raise

    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self._logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self._logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self._logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        self._logger.critical(*args, **kwargs)


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

    return CustomLogger(logger, dev_mode=settings.MODE == "development")


custom_logger = setup_logger()
