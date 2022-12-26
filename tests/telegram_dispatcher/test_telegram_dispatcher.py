from unittest.mock import ANY, MagicMock, patch

import pytest
from telegram.error import BadRequest, Forbidden
from telegram.ext import Application

from pdf_bot.command.command_service import CommandService
from pdf_bot.compare import CompareHandlers
from pdf_bot.feedback import FeedbackHandler
from pdf_bot.file import FileHandlers
from pdf_bot.image_handler import BatchImageHandler
from pdf_bot.merge import MergeHandlers
from pdf_bot.payment import PaymentService
from pdf_bot.telegram_dispatcher import TelegramDispatcher
from pdf_bot.text import TextHandlers
from pdf_bot.watermark import WatermarkHandlers
from pdf_bot.webpage import WebpageHandler
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestTelegramDispatcher(LanguageServiceTestMixin, TelegramTestMixin):
    SET_LANGUAGE = "set_lang"
    LANGUAGE = "🇺🇸 English (US)"
    PAYMENT = "payment"
    PAYMENT_INVOICE = "payment,"
    CALLBACK_DATA = "callback_data"

    def setup_method(self) -> None:
        super().setup_method()
        self.app = MagicMock(spec=Application)
        self.command_service = MagicMock(spec=CommandService)
        self.compare_handlers = MagicMock(spec=CompareHandlers)
        self.feedback_handler = MagicMock(spec=FeedbackHandler)
        self.file_handlers = MagicMock(spec=FileHandlers)
        self.image_handler = MagicMock(spec=BatchImageHandler)
        self.language_service = self.mock_language_service()
        self.merge_handlers = MagicMock(spec=MergeHandlers)
        self.payment_service = MagicMock(spec=PaymentService)
        self.text_handlers = MagicMock(spec=TextHandlers)
        self.watermark_handlers = MagicMock(spec=WatermarkHandlers)
        self.webpage_handler = MagicMock(spec=WebpageHandler)

        self.sut = TelegramDispatcher(
            self.command_service,
            self.compare_handlers,
            self.feedback_handler,
            self.file_handlers,
            self.image_handler,
            self.language_service,
            self.merge_handlers,
            self.payment_service,
            self.text_handlers,
            self.watermark_handlers,
            self.webpage_handler,
        )
        self.os_patcher = patch("pdf_bot.telegram_dispatcher.telegram_dispatcher.os")
        self.os = self.os_patcher.start()

    def teardown_method(self) -> None:
        self.os_patcher.stop()

    @pytest.mark.asyncio
    async def test_setup(self) -> None:
        self.os.environ = {"ADMIN_TELEGRAM_ID": 123}

        self.sut.setup(self.app)

        assert self.app.add_handler.call_count == 17
        self.app.add_error_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_without_admin_id(self) -> None:
        self.os.environ = {}

        self.sut.setup(self.app)

        assert self.app.add_handler.call_count == 16
        self.app.add_error_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_callback_query_set_language(self) -> None:
        self.telegram_callback_query.data = self.SET_LANGUAGE

        await self.sut.process_callback_query(
            self.telegram_update, self.telegram_context
        )

        self.language_service.send_language_options.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )
        self.telegram_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_callback_query_update_language(self) -> None:
        self.telegram_callback_query.data = self.LANGUAGE

        await self.sut.process_callback_query(
            self.telegram_update, self.telegram_context
        )

        self.language_service.update_user_language.assert_called_once_with(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_callback_query_payment(self) -> None:
        self.telegram_callback_query.data = self.PAYMENT

        await self.sut.process_callback_query(
            self.telegram_update, self.telegram_context
        )

        self.payment_service.send_support_options.assert_called_once_with(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_callback_query_payment_invoice(self) -> None:
        self.telegram_callback_query.data = self.PAYMENT_INVOICE

        await self.sut.process_callback_query(
            self.telegram_update, self.telegram_context
        )

        self.payment_service.send_invoice.assert_called_once_with(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_callback_query_answer_outdated(self) -> None:
        self.telegram_callback_query.answer.side_effect = BadRequest("Query is too old")
        await self.sut.process_callback_query(
            self.telegram_update, self.telegram_context
        )
        self.telegram_context.bot.send_message.assert_called_once_with(
            self.TELEGRAM_QUERY_USER_ID, ANY
        )

    @pytest.mark.asyncio
    async def test_process_callback_query_answer_unknown_bad_request(self) -> None:
        self.telegram_callback_query.answer.side_effect = BadRequest("Unknown error")
        with pytest.raises(BadRequest):
            await self.sut.process_callback_query(
                self.telegram_update, self.telegram_context
            )
            self.telegram_context.bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_callback_known_error(self) -> None:
        self.telegram_context.error = Forbidden("Error")
        await self.sut.error_callback(self.telegram_update, self.telegram_context)

    @pytest.mark.asyncio
    async def test_error_callback_unknown_error(self) -> None:
        exception = RuntimeError()
        self.telegram_context.error = exception

        with patch(
            "pdf_bot.telegram_dispatcher.telegram_dispatcher.sentry_sdk"
        ) as sentry_sdk:
            await self.sut.error_callback(self.telegram_update, self.telegram_context)

            self.telegram_update.message.reply_text.assert_called_once()
            sentry_sdk.capture_exception.assert_called_once_with(exception)
