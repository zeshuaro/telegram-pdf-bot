from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.pdf.models import FontData
from pdf_bot.telegram_internal import TelegramServiceError
from pdf_bot.text import TextRepository, TextService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestTextService(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    WAIT_TEXT = 0
    WAIT_FONT = 1
    FILE_PATH = "file_path"
    TEXT_KEY = "text"
    SKIP = "Skip"
    PDF_TEXT = "pdf_text"

    def setup_method(self) -> None:
        super().setup_method()
        self.font_data = MagicMock(spec=FontData)

        self.text_repository = MagicMock(spec=TextRepository)
        self.text_repository.get_font.return_value = self.font_data

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()

        self.telegram_service = self.mock_telegram_service()
        self.telegram_service.get_user_data.return_value = self.PDF_TEXT

        self.sut = TextService(
            self.text_repository,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    @pytest.mark.asyncio
    async def test_ask_pdf_text(self) -> None:
        actual = await self.sut.ask_pdf_text(
            self.telegram_update, self.telegram_context
        )
        assert actual == self.WAIT_TEXT
        self.telegram_service.reply_with_cancel_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_pdf_font(self) -> None:
        actual = await self.sut.ask_pdf_font(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_FONT
        self.telegram_context.user_data.__setitem__.assert_called_once_with(
            self.TEXT_KEY, self.TELEGRAM_TEXT
        )
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_pdf_font_cancel_option(self) -> None:
        self.telegram_message.text = "Cancel"

        actual = await self.sut.ask_pdf_font(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_context.user_data.__setitem__.assert_not_called()
        self.telegram_service.cancel_conversation.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_text(self) -> None:
        self.pdf_service.create_pdf_from_text.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.text_repository.get_font.assert_called_once_with(self.TELEGRAM_TEXT)
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.TEXT_KEY
        )
        self.pdf_service.create_pdf_from_text.assert_called_once_with(
            self.PDF_TEXT, self.font_data
        )
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.text_to_pdf,
        )

    @pytest.mark.asyncio
    async def test_check_text_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramServiceError()

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.text_repository.get_font.assert_called_once_with(self.TELEGRAM_TEXT)
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.TEXT_KEY
        )
        self.pdf_service.create_pdf_from_text.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_text_unknown_font(self) -> None:
        self.text_repository.get_font.return_value = None

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FONT
        self.text_repository.get_font.assert_called_once_with(self.TELEGRAM_TEXT)
        self.telegram_service.get_user_data.assert_not_called()
        self.pdf_service.create_pdf_from_text.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_text_skip_option(self) -> None:
        self.telegram_message.text = self.SKIP
        self.pdf_service.create_pdf_from_text.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.text_repository.get_font.assert_not_called()
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.TEXT_KEY
        )
        self.pdf_service.create_pdf_from_text.assert_called_once_with(
            self.PDF_TEXT, None
        )
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.text_to_pdf,
        )

    @pytest.mark.asyncio
    async def test_check_text_cancel_option(self) -> None:
        self.telegram_message.text = "Cancel"

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.text_repository.get_font.assert_not_called()
        self.telegram_service.get_user_data.assert_not_called()
        self.pdf_service.create_pdf_from_text.assert_not_called()
        self.telegram_service.send_file.assert_not_called()
