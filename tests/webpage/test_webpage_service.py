import hashlib
from unittest.mock import MagicMock, patch

import pytest
from weasyprint import HTML
from weasyprint.css.utils import InvalidValues
from weasyprint.urls import URLFetchingError

from pdf_bot.analytics import TaskType
from pdf_bot.io import IOService
from pdf_bot.telegram_internal import (
    TelegramGetUserDataError,
    TelegramUpdateUserDataError,
)
from pdf_bot.webpage import WebpageService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestWebpageService(LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin):
    URL = "https://example.com"
    HOSTNAME = "example.com"
    URL_HASH = hashlib.sha256(URL.encode("utf-8")).hexdigest()

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_message.text = self.URL

        self.io_service = MagicMock(spec=IOService)
        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = self.FILE_PATH

        self.telegram_service = self.mock_telegram_service()
        self.telegram_service.user_data_contains.return_value = False

        self.language_service = self.mock_language_service()
        self.sut = WebpageService(self.io_service, self.language_service, self.telegram_service)

        self.html = MagicMock(spec=HTML)
        self.html_cls_patcher = patch(
            "pdf_bot.webpage.webpage_service.HTML", return_value=self.html
        )
        self.html_cls = self.html_cls_patcher.start()

    def teardown_method(self) -> None:
        self.html_cls_patcher.stop()

    @pytest.mark.asyncio
    async def test_url_to_pdf(self) -> None:
        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self._assert_url_to_pdf_calls()
        self._assert_url_to_pdf_send_file()

    @pytest.mark.asyncio
    async def test_url_to_pdf_clear_cache_error(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramGetUserDataError

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self._assert_url_to_pdf_calls()
        self._assert_url_to_pdf_send_file()

    @pytest.mark.asyncio
    async def test_url_to_pdf_cache_error(self) -> None:
        self.telegram_service.update_user_data.side_effect = TelegramUpdateUserDataError

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self._assert_url_to_pdf_calls()
        self._assert_url_to_pdf_send_file()

    @pytest.mark.asyncio
    async def test_url_to_pdf_in_progress(self) -> None:
        self.telegram_service.user_data_contains.return_value = True

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self.telegram_service.user_data_contains.assert_called_once_with(
            self.telegram_context, self.URL_HASH
        )
        self.telegram_service.update_user_data.assert_not_called()
        self.io_service.create_temp_pdf_file.assert_not_called()
        self.html.write_pdf.assert_not_called()

        self.telegram_service.get_user_data.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.parametrize(
        "error",
        [
            URLFetchingError,
            AssertionError,
            AttributeError,
            IndexError,
            InvalidValues,
            KeyError,
            OverflowError,
            RuntimeError,
            ValueError,
        ],
    )
    @pytest.mark.asyncio
    async def test_url_to_pdf_error(self, error: type[Exception]) -> None:
        self.html.write_pdf.side_effect = error

        await self.sut.url_to_pdf(self.telegram_update, self.telegram_context)

        self._assert_url_to_pdf_calls()
        self.telegram_service.send_file.assert_not_called()
        assert self.telegram_update.effective_message.reply_text.call_count == 2

    def _assert_url_to_pdf_calls(self) -> None:
        self.telegram_service.user_data_contains.assert_called_once_with(
            self.telegram_context, self.URL_HASH
        )
        self.telegram_service.update_user_data.assert_called_once_with(
            self.telegram_context, self.URL_HASH, None
        )
        self.io_service.create_temp_pdf_file.assert_called_once_with(self.HOSTNAME)
        self.html.write_pdf.assert_called_once_with(self.FILE_PATH)

        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.URL_HASH
        )

    def _assert_url_to_pdf_send_file(self) -> None:
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.url_to_pdf,
        )
