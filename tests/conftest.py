import pytest

from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.image_processor import AbstractImageProcessor
from pdf_bot.pdf_processor import AbstractPdfProcessor


@pytest.fixture(autouse=True)
def _after_test() -> None:
    AbstractFileProcessor._FILE_PROCESSORS = {}  # noqa: SLF001
    AbstractImageProcessor._IMAGE_PROCESSORS = {}  # noqa: SLF001
    AbstractPdfProcessor._PDF_PROCESSORS = {}  # noqa: SLF001
