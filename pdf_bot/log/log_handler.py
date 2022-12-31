import logging
import sys

from loguru import logger
from sentry_sdk.integrations.logging import ignore_logger


class InterceptLoggingHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class MyLogHandler:
    _WEASYPRINT = "weasyprint"
    _FONT_TOOLS = "fontTools"

    def __init__(self, intercept_logging_handler: InterceptLoggingHandler) -> None:
        self.intercept_logging_handler = intercept_logging_handler

    def setup(self) -> None:
        logging.basicConfig(
            handlers=[self.intercept_logging_handler], level=logging.INFO, force=True
        )

        logging.getLogger(self._FONT_TOOLS).setLevel(logging.WARNING)

        logging.getLogger(self._WEASYPRINT).setLevel(logging.ERROR)
        ignore_logger(self._WEASYPRINT)
