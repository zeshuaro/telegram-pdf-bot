from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager, suppress
from gettext import gettext as _
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel
from telegram import (
    Bot,
    CallbackQuery,
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PhotoSize,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatAction, FileSizeLimit, MessageLimit, ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import AnalyticsService, EventAction, TaskType
from pdf_bot.consts import BACK, CANCEL, CHANNEL_NAME, FILE_DATA, MESSAGE_DATA
from pdf_bot.io_internal import IOService
from pdf_bot.language import LanguageService
from pdf_bot.models import BackData, FileData, MessageData, SupportData

from .exceptions import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramGetUserDataError,
    TelegramImageNotFoundError,
    TelegramUpdateUserDataError,
)


class _ReplyData(BaseModel):
    text: str
    markup_button_text: str
    parse_mode: ParseMode | None = None


class TelegramService:
    IMAGE_MIME_TYPE_PREFIX = "image"
    PDF_MIME_TYPE_SUFFIX = "pdf"
    PNG_SUFFIX = ".png"
    BACK = _("Back")
    MESSAGE_TRUNCATED = "\n..."

    def __init__(
        self,
        io_service: IOService,
        language_service: LanguageService,
        analytics_service: AnalyticsService,
        bot: Bot,
    ) -> None:
        self.io_service = io_service
        self.language_service = language_service
        self.analytics_service = analytics_service
        self.bot = bot

    @staticmethod
    def check_file_size(file: Document | PhotoSize) -> None:
        file_size = file.file_size
        if file_size is not None and file_size > FileSizeLimit.FILESIZE_DOWNLOAD:
            raise TelegramFileTooLargeError(
                _(
                    "Your file is too large for me to download and process, "
                    "please try again with a different file\n\n"
                    "Note that this limit is enforced by Telegram and there's "
                    "nothing I can do unless Telegram changes it"
                )
            )

    @staticmethod
    def check_file_upload_size(path: Path) -> None:
        if path.stat().st_size > FileSizeLimit.FILESIZE_UPLOAD:
            raise TelegramFileTooLargeError(
                _(
                    "The file is too large for me to send to you\n\n"
                    "Note that this limit is enforced by Telegram and there's "
                    "nothing I can do unless Telegram changes it"
                )
            )

    @staticmethod
    def get_user_data(context: ContextTypes.DEFAULT_TYPE, key: str) -> Any:
        """Get and pop value from user data by the provided key.

        Args:
            context (CallbackContext): the Telegram callback context
            key (str): the key for the value in user data

        Raises:
            TelegramUserDataError: if user_data does not exist or the key does not exist
                in user data

        Returns:
            Any: the value for the key
        """
        err = TelegramGetUserDataError(_("Something went wrong, please try again"))
        if context.user_data is None:
            raise err

        data = context.user_data.pop(key, None)
        if data is None:
            raise err
        return data

    @staticmethod
    def user_data_contains(context: ContextTypes.DEFAULT_TYPE, key: str) -> bool:
        return context.user_data is not None and key in context.user_data

    @staticmethod
    def update_user_data(context: ContextTypes.DEFAULT_TYPE, key: str, value: Any) -> None:
        if context.user_data is None:
            raise TelegramUpdateUserDataError(_("Something went wrong, please try again"))
        context.user_data[key] = value

    def get_file_data(self, context: ContextTypes.DEFAULT_TYPE) -> FileData:
        data: FileData = self.get_user_data(context, FILE_DATA)
        return data

    def cache_file_data(self, context: ContextTypes.DEFAULT_TYPE, file_data: FileData) -> None:
        self.update_user_data(context, FILE_DATA, file_data)

    def get_message_data(self, context: ContextTypes.DEFAULT_TYPE) -> MessageData:
        data: MessageData = self.get_user_data(context, MESSAGE_DATA)
        return data

    def cache_message_data(
        self, context: ContextTypes.DEFAULT_TYPE, message: Message | bool
    ) -> None:
        if not isinstance(message, Message):
            return

        with suppress(TelegramUpdateUserDataError):
            self.update_user_data(context, MESSAGE_DATA, MessageData.from_telegram_message(message))

    async def answer_query_and_drop_data(
        self, context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery
    ) -> None:
        await query.answer()
        with suppress(KeyError):
            context.drop_callback_data(query)

    def check_image(self, message: Message) -> Document | PhotoSize:
        img_file: Document | PhotoSize | None = message.document
        if (
            img_file is not None
            and isinstance(img_file, Document)
            and img_file.mime_type is not None
            and not img_file.mime_type.startswith(self.IMAGE_MIME_TYPE_PREFIX)
        ):
            raise TelegramFileMimeTypeError(_("Your file is not an image, please try again"))

        if img_file is None:
            if message.photo:
                img_file = message.photo[-1]
            else:
                raise TelegramImageNotFoundError(_("No image found in your message"))

        self.check_file_size(img_file)
        return img_file

    def check_pdf_document(self, message: Message) -> Document:
        doc = cast(Document, message.document)
        doc_mime_type = doc.mime_type

        if doc_mime_type is not None and not doc_mime_type.endswith(self.PDF_MIME_TYPE_SUFFIX):
            raise TelegramFileMimeTypeError(_("Your file is not a PDF file, please try again"))
        self.check_file_size(doc)
        return doc

    @asynccontextmanager
    async def download_pdf_file(self, file_id: str) -> AsyncGenerator[Path, None]:
        with self.io_service.create_temp_pdf_file() as path:
            file = await self.bot.get_file(file_id)
            await file.download_to_drive(custom_path=path)
            yield path

    @asynccontextmanager
    async def download_files(self, file_ids: list[str]) -> AsyncGenerator[list[Path], None]:
        with self.io_service.create_temp_files(len(file_ids)) as out_paths:
            for i, file_id in enumerate(file_ids):
                file = await self.bot.get_file(file_id)
                await file.download_to_drive(custom_path=out_paths[i])
            yield out_paths

    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        query: CallbackQuery | None = update.callback_query

        if query is not None:
            await self.answer_query_and_drop_data(context, query)
            await query.edit_message_text(_("Action cancelled"))
        else:
            msg = cast(Message, update.effective_message)
            await msg.reply_text(_("Action cancelled"), reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END

    def get_back_button(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> InlineKeyboardButton:
        _ = self.language_service.set_app_language(update, context)
        return InlineKeyboardButton(_(self.BACK), callback_data=BackData())

    def get_back_inline_markup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> InlineKeyboardMarkup:
        keyboard = [[self.get_back_button(update, context)]]
        return InlineKeyboardMarkup(keyboard)

    def get_support_markup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> InlineKeyboardMarkup:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [
                InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
                InlineKeyboardButton(_("Support PDF Bot"), callback_data=SupportData()),
            ]
        ]

        return InlineKeyboardMarkup(keyboard)

    def reply_with_back_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        parse_mode: ParseMode | None = None,
    ) -> Coroutine[Any, Any, Message]:
        data = _ReplyData(text=text, markup_button_text=BACK, parse_mode=parse_mode)
        return self._reply_with_markup(update, context, data)

    def reply_with_cancel_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        parse_mode: ParseMode | None = None,
    ) -> Coroutine[Any, Any, Message]:
        data = _ReplyData(text=text, markup_button_text=CANCEL, parse_mode=parse_mode)
        return self._reply_with_markup(update, context, data)

    async def send_file(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_path: Path,
        task: TaskType,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        chat_id = self._get_chat_id(update)

        try:
            self.check_file_upload_size(file_path)
        except TelegramFileTooLargeError as e:
            await self.bot.send_message(chat_id, _(str(e)))
            return

        reply_markup = self.get_support_markup(update, context)
        if file_path.suffix == self.PNG_SUFFIX:
            await self.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
            await self.bot.send_photo(
                chat_id,
                file_path,
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )
        else:
            await self.bot.send_chat_action(chat_id, ChatAction.UPLOAD_DOCUMENT)
            await self.bot.send_document(
                chat_id,
                file_path,
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )

        self.analytics_service.send_event(update, context, task, EventAction.complete)

    async def send_file_names(
        self, chat_id: int, text: str, file_data_list: list[FileData]
    ) -> None:
        msg_text = text
        for i, file_data in enumerate(file_data_list):
            file_name = file_data.name
            if file_name is None:
                file_name = "File name unavailable"
            msg_text += f"{i + 1}: {file_name}\n"

        if len(msg_text) > MessageLimit.MAX_TEXT_LENGTH:
            msg_text = (
                msg_text[: MessageLimit.MAX_TEXT_LENGTH - len(self.MESSAGE_TRUNCATED)]
                + self.MESSAGE_TRUNCATED
            )

        await self.bot.send_message(chat_id, msg_text)

    async def send_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        chat_id = self._get_chat_id(update)
        await self.bot.send_message(chat_id, _(text))

    @staticmethod
    def _get_chat_id(update: Update) -> int:
        query = update.callback_query
        msg: Message

        if query is None:
            msg = cast(Message, update.effective_message)
        else:
            msg = cast(Message, query.message)

        return msg.chat_id

    def _reply_with_markup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, reply_data: _ReplyData
    ) -> Coroutine[Any, Any, Message]:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        markup = ReplyKeyboardMarkup(
            [[_(reply_data.markup_button_text)]], one_time_keyboard=True, resize_keyboard=True
        )

        return msg.reply_text(
            _(reply_data.text), reply_markup=markup, parse_mode=reply_data.parse_mode
        )
