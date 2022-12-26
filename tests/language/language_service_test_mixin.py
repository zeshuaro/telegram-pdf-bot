from unittest.mock import AsyncMock

from pdf_bot.language import LanguageService


class LanguageServiceTestMixin:
    @staticmethod
    def mock_language_service() -> AsyncMock:
        service = AsyncMock(spec=LanguageService)
        service.set_app_language.return_value = lambda x: x
        return service
