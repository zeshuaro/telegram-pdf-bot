import gettext
from contextlib import contextmanager
from typing import Any, Generator, List

from telegram import Bot, Document, Message, PhotoSize
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import CallbackContext, Updater

from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.telegram.exceptions import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramImageNotFoundError,
    TelegramUserDataKeyError,
)

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


class TelegramService:
    IMAGE_MIME_TYPE_PREFIX = "image"
    PDF_MIME_TYPE_SUFFIX = "pdf"

    def __init__(
        self,
        io_service: IOService,
        updater: Updater | None = None,
        bot: Bot | None = None,
    ) -> None:
        self.io_service = io_service
        self.bot = bot or updater.bot

    @staticmethod
    def check_file_size(file: Document | PhotoSize) -> None:
        if file.file_size > MAX_FILESIZE_DOWNLOAD:
            raise TelegramFileTooLargeError(
                _(
                    "Your file is too large for me to download and process, "
                    "please try again with a differnt file\n\n"
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                )
            )

    def check_image(self, message: Message) -> Document | PhotoSize:
        img_file = message.document
        if img_file is not None and not img_file.mime_type.startswith(
            self.IMAGE_MIME_TYPE_PREFIX
        ):
            raise TelegramFileMimeTypeError(
                _("Your file is not an image, please try again")
            )

        if img_file is None:
            if message.photo:
                img_file = message.photo[-1]
            else:
                raise TelegramImageNotFoundError(_("No image found in your message"))

        self.check_file_size(img_file)
        return img_file

    def check_pdf_document(self, message: Message) -> Document:
        doc = message.document
        if not doc.mime_type.endswith(self.PDF_MIME_TYPE_SUFFIX):
            raise TelegramFileMimeTypeError(
                _("Your file is not a PDF file, please try again")
            )
        self.check_file_size(doc)
        return doc

    @contextmanager
    def download_file(self, file_id: str) -> Generator[str, None, None]:
        with self.io_service.create_temp_file() as out_path:
            file = self.bot.get_file(file_id)
            file.download(custom_path=out_path)
            yield out_path

    @contextmanager
    def download_files(self, file_ids: List[str]) -> Generator[List[str], None, None]:
        with self.io_service.create_temp_files(len(file_ids)) as out_paths:
            for i, file_id in enumerate(file_ids):
                file = self.bot.get_file(file_id)
                file.download(custom_path=out_paths[i])
            yield out_paths

    @staticmethod
    def get_user_data(context: CallbackContext, key: str) -> Any:
        """Get and pop value from user data by the provided key

        Args:
            context (CallbackContext): the Telegram callback context
            key (str): the key for the value in user data

        Raises:
            TelegramUserDataKeyError: if the key does not exist in user data

        Returns:
            Any: the value for the key
        """
        data = context.user_data.pop(key, None)
        if data is None:
            raise TelegramUserDataKeyError(_("Something went wrong, please try again"))
        return data

    def send_file_names(
        self, chat_id: str, text: str, file_data_list: List[FileData]
    ) -> None:
        for i, file_data in enumerate(file_data_list):
            text += f"{i + 1}: {file_data.name}\n"
        self.bot.send_message(chat_id, text)
