from telegram import Message, Update
from telegram.constants import FileSizeLimit
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pdf_bot.consts import (
    CANCEL,
    COMPRESS,
    CROP,
    DECRYPT,
    ENCRYPT,
    FILE_DATA,
    RENAME,
    ROTATE,
    SCALE,
    SPLIT,
    TEXT_FILTER,
)
from pdf_bot.crop import CropService
from pdf_bot.file.file_service import FileService
from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.file_task import FileTaskService
from pdf_bot.image_processor import ImageTaskProcessor
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.pdf_processor import (
    DecryptPdfProcessor,
    EncryptPdfProcessor,
    PdfTaskProcessor,
    RenamePdfProcessor,
    RotatePdfProcessor,
    ScalePdfProcessor,
    SplitPdfProcessor,
)
from pdf_bot.telegram_internal import TelegramService


class FileHandlers:
    WAIT_FILE_TASK = "wait_file_task"

    def __init__(
        self,
        file_task_service: FileTaskService,
        file_service: FileService,
        crop_service: CropService,
        decrypt_pdf_processor: DecryptPdfProcessor,
        encrypt_pdf_processor: EncryptPdfProcessor,
        rename_pdf_processor: RenamePdfProcessor,
        rotate_pdf_processor: RotatePdfProcessor,
        scale_pdf_processor: ScalePdfProcessor,
        split_pdf_processor: SplitPdfProcessor,
        telegram_service: TelegramService,
        language_service: LanguageService,
        image_task_processor: ImageTaskProcessor,
        pdf_task_processor: PdfTaskProcessor,
    ) -> None:
        self.file_task_service = file_task_service
        self.file_service = file_service
        self.crop_service = crop_service
        self.telegram_service = telegram_service
        self.image_task_processor = image_task_processor
        self.pdf_task_processor = pdf_task_processor
        self.language_service = language_service

        self.decrypt_pdf_processor = decrypt_pdf_processor
        self.encrypt_pdf_processor = encrypt_pdf_processor
        self.rename_pdf_processor = rename_pdf_processor
        self.rotate_pdf_processor = rotate_pdf_processor
        self.scale_pdf_processor = scale_pdf_processor
        self.split_pdf_processor = split_pdf_processor

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Document.PDF, self.check_doc),
                MessageHandler(
                    filters.PHOTO | filters.Document.IMAGE, self.check_image
                ),
            ],
            states={
                self.WAIT_FILE_TASK: AbstractFileProcessor.get_handlers()
                + [
                    CallbackQueryHandler(
                        self.telegram_service.cancel_conversation,
                        pattern=r"^cancel$",
                    ),
                    MessageHandler(TEXT_FILTER, self.check_doc_task),
                ],
                CropService.WAIT_CROP_TYPE: [
                    MessageHandler(TEXT_FILTER, self.crop_service.check_crop_type)
                ],
                CropService.WAIT_CROP_PERCENTAGE: [
                    MessageHandler(
                        TEXT_FILTER, self.crop_service.crop_pdf_by_percentage
                    )
                ],
                CropService.WAIT_CROP_MARGIN_SIZE: [
                    MessageHandler(
                        TEXT_FILTER, self.crop_service.crop_pdf_by_margin_size
                    )
                ],
                self.decrypt_pdf_processor.wait_password_state: [
                    MessageHandler(TEXT_FILTER, self.decrypt_pdf_processor.process_file)
                ],
                self.encrypt_pdf_processor.wait_password_state: [
                    MessageHandler(TEXT_FILTER, self.encrypt_pdf_processor.process_file)
                ],
                RenamePdfProcessor.WAIT_NEW_FILE_NAME: [
                    MessageHandler(TEXT_FILTER, self.rename_pdf_processor.rename_pdf)
                ],
                RotatePdfProcessor.WAIT_ROTATE_DEGREE: [
                    MessageHandler(TEXT_FILTER, self.rotate_pdf_processor.rotate_pdf)
                ],
                ScalePdfProcessor.WAIT_SCALE_TYPE: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_pdf_processor.check_scale_type
                    )
                ],
                ScalePdfProcessor.WAIT_SCALE_FACTOR: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_pdf_processor.scale_pdf_by_factor
                    )
                ],
                ScalePdfProcessor.WAIT_SCALE_DIMENSION: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_pdf_processor.scale_pdf_to_dimension
                    )
                ],
                SplitPdfProcessor.WAIT_SPLIT_RANGE: [
                    MessageHandler(TEXT_FILTER, self.split_pdf_processor.split_pdf)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation)
            ],
            allow_reentry=True,
        )

    async def check_doc(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        doc = update.effective_message.document  # type: ignore
        if doc.file_size >= FileSizeLimit.FILESIZE_DOWNLOAD:
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

            return ConversationHandler.END

        if not doc.mime_type.endswith("pdf"):
            return ConversationHandler.END

        context.user_data[FILE_DATA] = FileData.from_telegram_object(doc)  # type: ignore
        await self.file_task_service.ask_pdf_task(update, context)
        return await self.pdf_task_processor.ask_task(update, context)

    async def check_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int | str:
        message: Message = update.effective_message  # type: ignore
        file = message.document or message.photo[-1]

        if file.file_size >= FileSizeLimit.FILESIZE_DOWNLOAD:
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

            return ConversationHandler.END

        return await self.image_task_processor.ask_task(update, context)

    async def check_doc_task(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int | str:
        _ = self.language_service.set_app_language(update, context)
        text = update.effective_message.text  # type: ignore

        if text == _(CROP):
            return await self.crop_service.ask_crop_type(update, context)
        if text == _(DECRYPT):
            return await self.decrypt_pdf_processor.ask_password(update, context)
        if text == _(ENCRYPT):
            return await self.encrypt_pdf_processor.ask_password(update, context)
        if text == _(RENAME):
            return await self.rename_pdf_processor.ask_new_file_name(update, context)
        if text == _(ROTATE):
            return await self.rotate_pdf_processor.ask_degree(update, context)
        if text == _(SCALE):
            return await self.scale_pdf_processor.ask_scale_type(update, context)
        if text == _(SPLIT):
            return await self.split_pdf_processor.ask_split_range(update, context)
        if text == _(COMPRESS):
            return await self.file_service.compress_pdf(update, context)
        if text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)

        return FileTaskService.WAIT_FILE_TASK
