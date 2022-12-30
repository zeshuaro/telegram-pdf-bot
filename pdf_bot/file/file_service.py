from telegram import Message, Update
from telegram.constants import FileSizeLimit
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.image_processor import ImageTaskProcessor
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.pdf_processor import PdfTaskProcessor
from pdf_bot.telegram_internal import TelegramService


class FileService:
    def __init__(
        self,
        telegram_service: TelegramService,
        language_service: LanguageService,
        image_task_processor: ImageTaskProcessor,
        pdf_task_processor: PdfTaskProcessor,
    ) -> None:
        self.telegram_service = telegram_service
        self.image_task_processor = image_task_processor
        self.pdf_task_processor = pdf_task_processor
        self.language_service = language_service

    async def check_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        file_data = await self._get_file_data(update, context)
        if file_data is None:
            return ConversationHandler.END
        self.telegram_service.cache_file_data(context, file_data)

        return await self.pdf_task_processor.ask_task(update, context)

    async def check_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int | str:
        file_data = await self._get_file_data(update, context)
        if file_data is None:
            return ConversationHandler.END
        self.telegram_service.cache_file_data(context, file_data)

        return await self.image_task_processor.ask_task(update, context)

    async def _get_file_data(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> FileData | None:
        message: Message = update.effective_message  # type: ignore
        file = message.document or message.photo[-1]

        if file.file_size > FileSizeLimit.FILESIZE_DOWNLOAD:
            _ = self.language_service.set_app_language(update, context)
            await update.effective_message.reply_text(  # type: ignore
                "{desc_1}\n\n{desc_2}".format(
                    desc_1=_("Your file is too big for me to download and process"),
                    desc_2=_(
                        "Note that this is a Telegram Bot limitation and there's "
                        "nothing I can do unless Telegram changes this limit"
                    ),
                ),
            )
            return None
        return FileData.from_telegram_object(file)
