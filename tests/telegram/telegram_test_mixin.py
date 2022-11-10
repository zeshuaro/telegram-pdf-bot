from unittest.mock import MagicMock

from telegram import CallbackQuery, Document, Message, Update, User
from telegram.ext import CallbackContext


class TelegramTestMixin:
    @classmethod
    def setup_class(cls) -> None:
        cls.telegram_user_id = 0
        cls.telegram_document_id = "document_id"
        cls.telegram_document_name = "document_name"
        cls.telegram_text = "text"

    @classmethod
    def teardown_class(cls) -> None:
        pass

    def setup_method(self) -> None:
        self.telegram_user = MagicMock(spec=User)
        self.telegram_user.id = self.telegram_user_id

        self.telegram_document = MagicMock(spec=Document)
        self.telegram_document.file_id = self.telegram_document_id
        self.telegram_document.file_name = self.telegram_document_name

        self.telegram_message = MagicMock(spec=Message)
        self.telegram_message.from_user = self.telegram_user
        self.telegram_message.document = self.telegram_document
        self.telegram_message.text = self.telegram_text

        self.telegram_update = MagicMock(spec=Update)
        self.telegram_update.effective_message = self.telegram_message

        self.telegram_context = MagicMock(spec=CallbackContext)

        self.telegram_query = MagicMock(spec=CallbackQuery)
        self.telegram_query.from_user = self.telegram_user

    def teardown_method(self) -> None:
        pass
