import logging
import sys

from loguru import logger


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
    def __init__(self, intercept_logging_handler: InterceptLoggingHandler) -> None:
        self.intercept_logging_handler = intercept_logging_handler

    def setup(self) -> None:
        logging.basicConfig(
            handlers=[self.intercept_logging_handler], level=logging.INFO, force=True
        )

        weasyprint_logger = logging.getLogger("weasyprint")
        weasyprint_logger.setLevel(logging.WARNING)
