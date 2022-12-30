from unittest.mock import patch

import pytest
from telegram.error import BadRequest, Forbidden

from pdf_bot.error import ErrorHandler
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestErrorHandler(LanguageServiceTestMixin, TelegramTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = ErrorHandler(self.language_service)

        self.sentry_sdk_patcher = patch("pdf_bot.error.error_handler.sentry_sdk")
        self.sentry_sdk = self.sentry_sdk_patcher.start()

    def teardown_method(self) -> None:
        self.sentry_sdk_patcher.stop()

    @pytest.mark.asyncio
    async def test_callback_known_error(self) -> None:
        self.telegram_context.error = Forbidden("Error")
        await self.sut.callback(self.telegram_update, self.telegram_context)

    @pytest.mark.asyncio
    async def test_callback_unknown_error(self) -> None:
        error = RuntimeError()
        self.telegram_context.error = error

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_called_once()
        self.sentry_sdk.capture_exception.assert_called_once_with(error)

    @pytest.mark.asyncio
    async def test_callback_unknown_error_and_send_message_error(self) -> None:
        error = RuntimeError()
        self.telegram_context.error = error
        self.telegram_context.bot.send_message.side_effect = Exception

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_called_once()
        self.sentry_sdk.capture_exception.assert_called_once_with(error)

    @pytest.mark.asyncio
    async def test_callback_unknown_error_and_without_chat_id(self) -> None:
        error = RuntimeError()
        self.telegram_context.error = error
        self.telegram_update.effective_message = None
        self.telegram_update.effective_chat = None

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_not_called()
        self.sentry_sdk.capture_exception.assert_called_once_with(error)

    @pytest.mark.asyncio
    async def test_callback_unknown_error_and_effective_chat(self) -> None:
        error = RuntimeError()
        self.telegram_context.error = error
        self.telegram_update.effective_message = None
        self.telegram_update.effective_chat = self.telegram_chat

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_called_once()
        self.sentry_sdk.capture_exception.assert_called_once_with(error)

    @pytest.mark.asyncio
    async def test_callback_unknown_error_and_not_update(self) -> None:
        error = RuntimeError()
        self.telegram_context.error = error

        await self.sut.callback(None, self.telegram_context)

        self.telegram_context.bot.send_message.assert_not_called()
        self.sentry_sdk.capture_exception.assert_called_once_with(error)

    @pytest.mark.asyncio
    async def test_callback_without_error(self) -> None:
        self.telegram_context.error = None

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_not_called()
        self.sentry_sdk.capture_exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_bad_request_message_not_modified(self) -> None:
        self.telegram_context.error = BadRequest("Message is not modified")

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_not_called()
        self.sentry_sdk.capture_exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_bad_request_query_outdated(self) -> None:
        self.telegram_context.error = BadRequest(
            "Query is too old and response timeout expired"
        )

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_called_once()
        self.sentry_sdk.capture_exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_unknown_bad_request(self) -> None:
        error = BadRequest("Unknown bad request")
        self.telegram_context.error = error

        await self.sut.callback(self.telegram_update, self.telegram_context)

        self.telegram_context.bot.send_message.assert_called_once()
        self.sentry_sdk.capture_exception.assert_called_once_with(error)
