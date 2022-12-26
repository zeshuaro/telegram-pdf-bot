from unittest.mock import AsyncMock

from telegram.ext import ConversationHandler

from pdf_bot.telegram_internal import TelegramService
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TelegramServiceTestMixin(TelegramTestMixin):
    def mock_telegram_service(self) -> AsyncMock:
        service = AsyncMock(spec=TelegramService)
        service.check_pdf_document.return_value = self.telegram_document
        service.check_image.return_value = self.telegram_document
        service.get_user_data.return_value = (
            self.TELEGRAM_DOCUMENT_ID,
            self.TELEGRAM_DOCUMENT_NAME,
        )
        service.cancel_conversation.return_value = ConversationHandler.END
        service.reply_with_cancel_markup.side_effect = self.telegram_message
        service.reply_with_back_markup.side_effect = self.telegram_message

        return service
