import logging
import sys

from loguru import logger
from sentry_sdk.integrations.logging import ignore_logger


class InterceptLoggingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6  # noqa: SLF001
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class MyLogHandler:
    _FONT_TOOLS = "fontTools"
    _WEASYPRINT_LOGGERS = ("weasyprint", "weasyprint.pdf.anchors", "weasyprint.images")

    def __init__(self, intercept_logging_handler: InterceptLoggingHandler) -> None:
        self.intercept_logging_handler = intercept_logging_handler

    def setup(self) -> None:
        logging.basicConfig(
            handlers=[self.intercept_logging_handler], level=logging.INFO, force=True
        )

        logging.getLogger(self._FONT_TOOLS).setLevel(logging.WARNING)
        ignore_logger(self._FONT_TOOLS)

        for logger_name in self._WEASYPRINT_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
            ignore_logger(logger_name)
