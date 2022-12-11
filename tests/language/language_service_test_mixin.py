from unittest.mock import MagicMock

from pdf_bot.language import LanguageService


class LanguageServiceTestMixin:
    @staticmethod
    def mock_language_service() -> MagicMock:
        service = MagicMock(spec=LanguageService)
        service.set_app_language.return_value = lambda x: x
        return service
