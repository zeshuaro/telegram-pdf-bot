import gettext
from contextlib import contextmanager
from typing import Any, Generator, List

from telegram import Bot, Document, Message
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import CallbackContext, Updater

from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.telegram.exceptions import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramUserDataKeyError,
)

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


class TelegramService:
    def __init__(
        self,
        io_service: IOService,
        updater: Updater | None = None,
        bot: Bot | None = None,
    ) -> None:
        self.io_service = io_service
        self.bot = bot or updater.bot

    @staticmethod
    def check_pdf_document(message: Message) -> Document:
        doc = message.document
        if not doc.mime_type.endswith("pdf"):
            raise TelegramFileMimeTypeError(
                _(
                    "Your file is not a PDF file, please try again "
                    "and ensure that your file has the .pdf extension"
                )
            )
        if doc.file_size > MAX_FILESIZE_DOWNLOAD:
            raise TelegramFileTooLargeError(
                "Your file is too large for me to download and process, "
                "please try again with a differnt file\n\n"
                "Note that this is a Telegram Bot limitation and there's "
                "nothing I can do unless Telegram changes this limit"
            )

        return doc

    @contextmanager
    def download_file(self, file_id: str) -> Generator[str, None, None]:
        with self.io_service.create_temp_file() as out_path:
            try:
                file = self.bot.get_file(file_id)
                file.download(custom_path=out_path)
                yield out_path
            finally:
                pass

    @contextmanager
    def download_files(self, file_ids: List[str]) -> Generator[List[str], None, None]:
        with self.io_service.create_temp_files(len(file_ids)) as out_paths:
            try:
                for i, file_id in enumerate(file_ids):
                    file = self.bot.get_file(file_id)
                    file.download(custom_path=out_paths[i])
                yield out_paths
            finally:
                pass

    def get_user_data(self, context: CallbackContext, key: str) -> Any:
        return self._get_user_data(context, key)

    def get_and_pop_user_data(self, context: CallbackContext, key: str) -> Any:
        return self._get_user_data(context, key, is_pop=True)

    def send_file_names(
        self, chat_id: str, text: str, file_data_list: List[FileData]
    ) -> None:
        for i, file_data in enumerate(file_data_list):
            text += f"{i + 1}: {file_data.name}\n"
        self.bot.send_message(chat_id, text)

    @staticmethod
    def _get_user_data(context: CallbackContext, key: str, is_pop=False) -> Any:
        user_data = context.user_data
        value = user_data.pop(key, None) if is_pop else user_data.get(key, None)

        if value is None:
            raise TelegramUserDataKeyError(_("Something went wrong, please try again"))
        return value
