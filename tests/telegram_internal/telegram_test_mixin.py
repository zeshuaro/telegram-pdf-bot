from unittest.mock import MagicMock

from telegram import (
    Bot,
    CallbackQuery,
    Chat,
    Document,
    File,
    Message,
    PhotoSize,
    PreCheckoutQuery,
    Update,
    User,
)
from telegram.ext import CallbackContext


class TelegramTestMixin:
    @classmethod
    def setup_class(cls) -> None:
        cls.telegram_user_id = 0
        cls.telegram_query_user_id = 1
        cls.telegram_username = "username"
        cls.telegram_file_id = "file_id"
        cls.telegram_document_id = "document_id"
        cls.telegram_document_name = "document_name"
        cls.telegram_photo_size_id = "photo_size_id"
        cls.telegram_text = "text"
        cls.telegram_chat_id = "chat_id"

    @classmethod
    def teardown_class(cls) -> None:
        pass

    def setup_method(self) -> None:
        self.telegram_bot = MagicMock(spec=Bot)

        self.telegram_user = MagicMock(spec=User)
        self.telegram_user.id = self.telegram_user_id
        self.telegram_user.username = self.telegram_username

        self.telegram_query_user = MagicMock(spec=User)
        self.telegram_query_user.id = self.telegram_query_user_id

        self.telegram_chat = MagicMock(spec=Chat)
        self.telegram_chat.id = self.telegram_chat_id

        self.telegram_file = MagicMock(spec=File)
        self.telegram_file.file_id = self.telegram_file_id

        self.telegram_document = MagicMock(spec=Document)
        self.telegram_document.file_id = self.telegram_document_id
        self.telegram_document.file_name = self.telegram_document_name

        self.telegram_photo_size = MagicMock(spec=PhotoSize)
        self.telegram_photo_size.file_id = self.telegram_photo_size_id

        self.telegram_message = MagicMock(spec=Message)
        self.telegram_message.chat = self.telegram_chat
        self.telegram_message.from_user = self.telegram_user
        self.telegram_message.document = self.telegram_document
        self.telegram_message.text = self.telegram_text

        self.telegram_pre_checkout_query = MagicMock(spec=PreCheckoutQuery)

        self.telegram_update = MagicMock(spec=Update)
        self.telegram_update.effective_message = self.telegram_message
        self.telegram_update.pre_checkout_query = self.telegram_pre_checkout_query

        self.telegram_user_data = MagicMock(spec=dict)
        self.telegram_context = MagicMock(spec=CallbackContext)
        self.telegram_context.bot = self.telegram_bot
        self.telegram_context.user_data = self.telegram_user_data

        self.telegram_callback_query = MagicMock(spec=CallbackQuery)
        self.telegram_callback_query.from_user = self.telegram_query_user

    def teardown_method(self) -> None:
        pass
