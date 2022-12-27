from typing import Any
from unittest.mock import AsyncMock

from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.consts import FILE_DATA, MESSAGE_DATA
from pdf_bot.models import FileData, MessageData
from pdf_bot.telegram_internal import TelegramService
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TelegramServiceTestMixin(TelegramTestMixin):
    def mock_telegram_service(self) -> AsyncMock:
        service = AsyncMock(spec=TelegramService)
        service.check_pdf_document.return_value = self.telegram_document
        service.check_image.return_value = self.telegram_document
        service.cancel_conversation.return_value = ConversationHandler.END
        service.reply_with_cancel_markup.side_effect = self.telegram_message
        service.reply_with_back_markup.side_effect = self.telegram_message

        def get_user_data(_context: ContextTypes.DEFAULT_TYPE, key: str) -> Any:
            if key == FILE_DATA:
                return FileData(self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME)
            if key == MESSAGE_DATA:
                return MessageData(self.TELEGRAM_CHAT_ID, self.TELEGRAM_MESSAGE_ID)
            return None

        service.get_user_data.side_effect = get_user_data

        return service
