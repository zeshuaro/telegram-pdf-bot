import os
from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import Any, AsyncGenerator, Coroutine, List

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
from telegram.constants import ChatAction, FileSizeLimit, ParseMode
from telegram.ext import Application, ContextTypes, ConversationHandler

from pdf_bot.analytics import AnalyticsService, EventAction, TaskType
from pdf_bot.consts import BACK, CANCEL, CHANNEL_NAME, PAYMENT
from pdf_bot.io import IOService
from pdf_bot.language import LanguageService
from pdf_bot.models import BackData, FileData
from pdf_bot.telegram_internal.exceptions import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramImageNotFoundError,
    TelegramUserDataKeyError,
)


class TelegramService:
    IMAGE_MIME_TYPE_PREFIX = "image"
    PDF_MIME_TYPE_SUFFIX = "pdf"
    PNG_SUFFIX = ".png"
    BACK = _("Back")

    def __init__(
        self,
        io_service: IOService,
        language_service: LanguageService,
        analytics_service: AnalyticsService,
        telegram_app: Application | None = None,
        bot: Bot | None = None,
    ) -> None:
        self.io_service = io_service
        self.language_service = language_service
        self.analytics_service = analytics_service
        self.bot = bot or telegram_app.bot  # type: ignore

    @staticmethod
    def check_file_size(file: Document | PhotoSize) -> None:
        if file.file_size > FileSizeLimit.FILESIZE_DOWNLOAD:
            raise TelegramFileTooLargeError(
                _(
                    "Your file is too large for me to download and process, "
                    "please try again with a differnt file\n\n"
                    "Note that this limit is enforced by Telegram and there's "
                    "nothing I can do unless Telegram changes it"
                )
            )

    @staticmethod
    def check_file_upload_size(path: str) -> None:
        if os.path.getsize(path) > FileSizeLimit.FILESIZE_UPLOAD:
            raise TelegramFileTooLargeError(
                _(
                    "The file is too large for me to send to you\n\n"
                    "Note that this limit is enforced by Telegram and there's "
                    "nothing I can do unless Telegram changes it"
                )
            )

    @staticmethod
    def get_user_data(context: ContextTypes.DEFAULT_TYPE, key: str) -> Any:
        """Get and pop value from user data by the provided key

        Args:
            context (CallbackContext): the Telegram callback context
            key (str): the key for the value in user data

        Raises:
            TelegramUserDataKeyError: if the key does not exist in user data

        Returns:
            Any: the value for the key
        """
        data = context.user_data.pop(key, None)  # type: ignore
        if data is None:
            raise TelegramUserDataKeyError(_("Something went wrong, please try again"))
        return data

    def check_image(self, message: Message) -> Document | PhotoSize:
        img_file: Document | PhotoSize | None = message.document
        if (
            img_file is not None
            and isinstance(img_file, Document)
            and not img_file.mime_type.startswith(self.IMAGE_MIME_TYPE_PREFIX)
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

    @asynccontextmanager
    async def download_pdf_file(self, file_id: str) -> AsyncGenerator[str, None]:
        with self.io_service.create_temp_pdf_file() as path:
            file = await self.bot.get_file(file_id)
            await file.download_to_drive(custom_path=path)
            yield path

    @asynccontextmanager
    async def download_files(
        self, file_ids: List[str]
    ) -> AsyncGenerator[list[str], None]:
        with self.io_service.create_temp_files(len(file_ids)) as out_paths:
            for i, file_id in enumerate(file_ids):
                file = await self.bot.get_file(file_id)
                await file.download_to_drive(custom_path=out_paths[i])
            yield out_paths

    async def cancel_conversation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        query: CallbackQuery | None = update.callback_query

        if query is not None:
            await query.answer()
            await query.edit_message_text(_("Action cancelled"))
        else:
            await update.effective_message.reply_text(  # type: ignore
                _("Action cancelled"), reply_markup=ReplyKeyboardRemove()
            )

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
                InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
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
        return self._reply_with_markup(update, context, text, BACK, parse_mode)

    def reply_with_cancel_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        parse_mode: ParseMode | None = None,
    ) -> Coroutine[Any, Any, Message]:
        return self._reply_with_markup(update, context, text, CANCEL, parse_mode)

    async def send_file(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_path: str,
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
        if file_path.endswith(self.PNG_SUFFIX):
            await self.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
            await self.bot.send_photo(
                chat_id,
                open(file_path, "rb"),
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )
        else:
            await self.bot.send_chat_action(chat_id, ChatAction.UPLOAD_DOCUMENT)
            await self.bot.send_document(
                chat_id,
                document=open(file_path, "rb"),
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )

        self.analytics_service.send_event(update, context, task, EventAction.complete)

    async def send_file_names(
        self, chat_id: int, text: str, file_data_list: List[FileData]
    ) -> None:
        for i, file_data in enumerate(file_data_list):
            file_name = file_data.name
            if file_name is None:
                file_name = "File name unavailable"
            text += f"{i + 1}: {file_name}\n"
        await self.bot.send_message(chat_id, text)

    @staticmethod
    def _get_chat_id(update: Update) -> int:
        query: CallbackQuery | None = update.callback_query
        if query is not None:
            return query.message.chat_id
        return update.effective_message.chat_id  # type: ignore

    def _reply_with_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        markup_text: str,
        parse_mode: ParseMode | None = None,
    ) -> Coroutine[Any, Any, Message]:
        _ = self.language_service.set_app_language(update, context)
        markup = ReplyKeyboardMarkup(
            [[_(markup_text)]], one_time_keyboard=True, resize_keyboard=True
        )
        return update.effective_message.reply_text(  # type: ignore
            _(text), reply_markup=markup, parse_mode=parse_mode
        )
