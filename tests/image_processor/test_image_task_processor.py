from pdf_bot.image_processor import AbstractImageProcessor, ImageTaskProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestImageTaskProcessor(
    LanguageServiceTestMixin,
    TelegramTestMixin,
):
    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = ImageTaskProcessor(self.language_service)

    def test_processor_type(self) -> None:
        actual = self.sut.processor_type
        assert actual == AbstractImageProcessor
