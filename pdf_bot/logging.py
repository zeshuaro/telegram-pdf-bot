import logging
import sys

from logbook import StreamHandler
from logbook.compat import redirect_logging


def setup_logging():
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("ocrmypdf").setLevel(logging.WARNING)
    redirect_logging()

    format_string = "{record.level_name}: {record.message}"
    StreamHandler(
        sys.stdout, format_string=format_string, level="INFO"
    ).push_application()
