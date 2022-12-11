from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.telegram_internal import TelegramService
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TelegramServiceTestMixin(TelegramTestMixin):
    def mock_telegram_service(self) -> MagicMock:
        service = MagicMock(spec=TelegramService)
        service.check_pdf_document.return_value = self.telegram_document
        service.check_image.return_value = self.telegram_document
        service.get_user_data.return_value = (
            self.TELEGRAM_DOCUMENT_ID,
            self.TELEGRAM_DOCUMENT_NAME,
        )
        service.cancel_conversation.return_value = ConversationHandler.END

        return service
