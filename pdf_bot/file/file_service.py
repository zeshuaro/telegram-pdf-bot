from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import FILE_DATA
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError


class FileService:
    def __init__(
        self,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    async def compress_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.message

        try:
            file_data: FileData = self.telegram_service.get_user_data(
                context, FILE_DATA
            )
        except TelegramServiceError as e:
            await message.reply_text(_(str(e)))
            return ConversationHandler.END

        async with self.pdf_service.compress_pdf(file_data.id) as compress_result:
            await message.reply_text(
                _(
                    "File size reduced by {percent}, from {old_size} to {new_size}"
                ).format(
                    percent="<b>{:.0%}</b>".format(compress_result.reduced_percentage),
                    old_size=f"<b>{compress_result.readable_old_size}</b>",
                    new_size=f"<b>{compress_result.readable_new_size}</b>",
                ),
                parse_mode=ParseMode.HTML,
            )
            await self.telegram_service.send_file(
                update, context, compress_result.out_path, TaskType.compress_pdf
            )
        return ConversationHandler.END
