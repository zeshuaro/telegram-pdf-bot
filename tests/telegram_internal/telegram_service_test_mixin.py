from typing import Callable
from unittest.mock import AsyncMock

from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.models import FileData
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
        service.get_file_data.return_value = self.FILE_DATA
        service.get_message_data.return_value = self.MESSAGE_DATA
        service.get_back_inline_markup.return_value = self.BACK_INLINE_MARKUP

        return service

    def get_file_data_side_effect_by_index(
        self, *file_data_args: FileData
    ) -> Callable[[ContextTypes.DEFAULT_TYPE], FileData]:
        index = 0

        def get_file_data(_context: ContextTypes.DEFAULT_TYPE) -> FileData:
            nonlocal index
            data = file_data_args[index]
            index += 1
            return data  # noqa: UnnecessaryAssign

        return get_file_data
