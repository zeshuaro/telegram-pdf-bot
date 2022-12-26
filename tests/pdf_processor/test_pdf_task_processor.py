from pdf_bot.pdf_processor import AbstractPdfProcessor, PdfTaskProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestPdfTaskProcessor(
    LanguageServiceTestMixin,
    TelegramTestMixin,
):
    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = PdfTaskProcessor(self.language_service)

    def test_processor_type(self) -> None:
        actual = self.sut.processor_type
        assert actual == AbstractPdfProcessor
