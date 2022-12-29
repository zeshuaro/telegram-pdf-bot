from typing import Any
from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.webpage import WebpageHandler, WebpageService, WebpageServiceError
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin


class TestWebpageHandler(LanguageServiceTestMixin, TelegramServiceTestMixin):
    URL = "https://example.com"

    URLS = "urls"

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_message.text = self.URL

        self.webpage_service = MagicMock(spec=WebpageService)
        self.webpage_service.url_to_pdf.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = WebpageHandler(
            self.webpage_service, self.language_service, self.telegram_service
        )

    @pytest.mark.asyncio
    async def test_url_to_pdf(self) -> None:
        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.URLS, {self.URL}
        )
        self.webpage_service.url_to_pdf.assert_called_once_with(self.URL)
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.url_to_pdf,
        )

    @pytest.mark.asyncio
    async def test_url_to_pdf_webpage_service_error(self) -> None:
        self.webpage_service.url_to_pdf.side_effect = WebpageServiceError()

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.URLS, {self.URL}
        )
        self.webpage_service.url_to_pdf.assert_called_once_with(self.URL)
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_url_to_pdf_url_set_exists(self) -> None:
        user_data: dict[str, Any] = {self.URLS: set()}
        self.telegram_user_data.__contains__.side_effect = user_data.__contains__

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self.telegram_user_data.__setitem__.assert_not_called()
        self.webpage_service.url_to_pdf.assert_called_once_with(self.URL)
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.url_to_pdf,
        )

    @pytest.mark.asyncio
    async def test_url_to_pdf_url_in_process(self) -> None:
        user_data = {self.URLS: {self.URL}}
        self.telegram_context.user_data = user_data

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self.telegram_user_data.__setitem__.assert_not_called()
        self.webpage_service.url_to_pdf.assert_not_called()
        self.telegram_service.send_file.assert_not_called()
