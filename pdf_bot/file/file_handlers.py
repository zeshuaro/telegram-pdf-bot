from telegram import Update
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from pdf_bot.consts import (
    BEAUTIFY,
    BLACK_AND_WHITE,
    CANCEL,
    COMPRESS,
    CROP,
    DECRYPT,
    ENCRYPT,
    EXTRACT_IMAGE,
    EXTRACT_TEXT,
    FILE_DATA,
    OCR,
    PREVIEW,
    RENAME,
    ROTATE,
    SCALE,
    SPLIT,
    TEXT_FILTER,
    TO_IMAGES,
    TO_PDF,
    WAIT_IMAGE_TASK,
)
from pdf_bot.crop import CropService
from pdf_bot.file.file_service import FileService
from pdf_bot.file_task import FileTaskService
from pdf_bot.image_processor import BeautifyImageProcessor, ImageToPDFProcessor
from pdf_bot.language import LanguageService
from pdf_bot.pdf_processor import (
    DecryptPDFProcessor,
    EncryptPDFProcessor,
    ExtractPDFImageProcessor,
    ExtractPDFTextProcessor,
    GrayscalePDFProcessor,
    OCRPDFProcessor,
    PDFToImageProcessor,
    PreviewPDFProcessor,
    RenamePDFProcessor,
    RotatePDFProcessor,
    ScalePDFProcessor,
    SplitPDFProcessor,
)
from pdf_bot.telegram_internal import TelegramService


class FileHandlers:
    def __init__(
        self,
        file_task_service: FileTaskService,
        file_service: FileService,
        crop_service: CropService,
        decrypt_pdf_processor: DecryptPDFProcessor,
        encrypt_pdf_processor: EncryptPDFProcessor,
        extract_pdf_image_processor: ExtractPDFImageProcessor,
        extract_pdf_text_processor: ExtractPDFTextProcessor,
        grayscale_pdf_processor: GrayscalePDFProcessor,
        ocr_pdf_processor: OCRPDFProcessor,
        pdf_to_image_processor: PDFToImageProcessor,
        preview_pdf_processor: PreviewPDFProcessor,
        rename_pdf_processor: RenamePDFProcessor,
        rotate_pdf_processor: RotatePDFProcessor,
        scale_pdf_processor: ScalePDFProcessor,
        split_pdf_processor: SplitPDFProcessor,
        beautify_image_processor: BeautifyImageProcessor,
        image_to_pdf_processor: ImageToPDFProcessor,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.file_task_service = file_task_service
        self.file_service = file_service
        self.crop_service = crop_service
        self.telegram_service = telegram_service
        self.language_service = language_service

        self.decrypt_pdf_processor = decrypt_pdf_processor
        self.encrypt_pdf_processor = encrypt_pdf_processor
        self.extract_pdf_image_processor = extract_pdf_image_processor
        self.extract_pdf_text_processor = extract_pdf_text_processor
        self.grayscale_pdf_processor = grayscale_pdf_processor
        self.ocr_pdf_processor = ocr_pdf_processor
        self.pdf_to_image_processor = pdf_to_image_processor
        self.preview_pdf_processor = preview_pdf_processor
        self.rename_pdf_processor = rename_pdf_processor
        self.rotate_pdf_processor = rotate_pdf_processor
        self.scale_pdf_processor = scale_pdf_processor
        self.split_pdf_processor = split_pdf_processor

        self.beautify_image_processor = beautify_image_processor
        self.image_to_pdf_processor = image_to_pdf_processor

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(Filters.document, self.check_doc),
                MessageHandler(Filters.photo, self.check_image),
            ],
            states={
                FileTaskService.WAIT_PDF_TASK: [
                    MessageHandler(TEXT_FILTER, self.check_doc_task)
                ],
                FileTaskService.WAIT_IMAGE_TASK: [
                    MessageHandler(TEXT_FILTER, self.check_image_task)
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
                RenamePDFProcessor.WAIT_NEW_FILE_NAME: [
                    MessageHandler(TEXT_FILTER, self.rename_pdf_processor.rename_pdf)
                ],
                RotatePDFProcessor.WAIT_ROTATE_DEGREE: [
                    MessageHandler(TEXT_FILTER, self.rotate_pdf_processor.rotate_pdf)
                ],
                ScalePDFProcessor.WAIT_SCALE_TYPE: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_pdf_processor.check_scale_type
                    )
                ],
                ScalePDFProcessor.WAIT_SCALE_FACTOR: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_pdf_processor.scale_pdf_by_factor
                    )
                ],
                ScalePDFProcessor.WAIT_SCALE_DIMENSION: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_pdf_processor.scale_pdf_to_dimension
                    )
                ],
                SplitPDFProcessor.WAIT_SPLIT_RANGE: [
                    MessageHandler(TEXT_FILTER, self.split_pdf_processor.split_pdf)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation)
            ],
            allow_reentry=True,
            run_async=True,
        )

    def check_doc(self, update: Update, context: CallbackContext) -> str | int:
        doc = update.effective_message.document  # type: ignore
        if doc.file_size >= MAX_FILESIZE_DOWNLOAD:
            _ = self.language_service.set_app_language(update, context)
            update.effective_message.reply_text(  # type: ignore
                "{desc_1}\n\n{desc_2}".format(
                    desc_1=_("Your file is too big for me to download and process"),
                    desc_2=_(
                        "Note that this is a Telegram Bot limitation and there's "
                        "nothing I can do unless Telegram changes this limit"
                    ),
                ),
            )

            return ConversationHandler.END

        if doc.mime_type.startswith("image"):
            context.user_data[FILE_DATA] = doc.file_id, doc.file_name  # type: ignore
            return self.file_task_service.ask_image_task(update, context)
        if not doc.mime_type.endswith("pdf"):
            return ConversationHandler.END

        context.user_data[FILE_DATA] = doc.file_id, doc.file_name  # type: ignore
        return self.file_task_service.ask_pdf_task(update, context)

    def check_image(self, update: Update, context: CallbackContext) -> int | str:
        image = update.effective_message.photo[-1]  # type: ignore
        if image.file_size >= MAX_FILESIZE_DOWNLOAD:
            _ = self.language_service.set_app_language(update, context)
            update.effective_message.reply_text(  # type: ignore
                "{desc_1}\n\n{desc_2}".format(
                    desc_1=_("Your file is too big for me to download and process"),
                    desc_2=_(
                        "Note that this is a Telegram Bot limitation and there's "
                        "nothing I can do unless Telegram changes this limit"
                    ),
                ),
            )

            return ConversationHandler.END

        context.user_data[FILE_DATA] = image.file_id, None  # type: ignore
        return self.file_task_service.ask_image_task(update, context)

    def check_doc_task(self, update: Update, context: CallbackContext) -> int | str:
        _ = self.language_service.set_app_language(update, context)
        text = update.effective_message.text  # type: ignore

        if text == _(CROP):
            return self.crop_service.ask_crop_type(update, context)
        if text == _(DECRYPT):
            return self.decrypt_pdf_processor.ask_password(update, context)
        if text == _(ENCRYPT):
            return self.encrypt_pdf_processor.ask_password(update, context)
        if text == _(TO_IMAGES):
            return self.pdf_to_image_processor.process_file(update, context)
        if text == _(EXTRACT_IMAGE):
            return self.extract_pdf_image_processor.process_file(update, context)
        if text == _(PREVIEW):
            return self.preview_pdf_processor.process_file(update, context)
        if text == _(RENAME):
            return self.rename_pdf_processor.ask_new_file_name(update, context)
        if text == _(ROTATE):
            return self.rotate_pdf_processor.ask_degree(update, context)
        if text == _(SCALE):
            return self.scale_pdf_processor.ask_scale_type(update, context)
        if text == _(SPLIT):
            return self.split_pdf_processor.ask_split_range(update, context)
        if text == _(EXTRACT_TEXT):
            return self.extract_pdf_text_processor.process_file(update, context)
        if text == OCR:
            return self.ocr_pdf_processor.process_file(update, context)
        if text == _(COMPRESS):
            return self.file_service.compress_pdf(update, context)
        if text == _(BLACK_AND_WHITE):
            return self.grayscale_pdf_processor.process_file(update, context)
        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)

        return FileTaskService.WAIT_PDF_TASK

    def check_image_task(self, update: Update, context: CallbackContext) -> int | str:
        _ = self.language_service.set_app_language(update, context)
        text = update.effective_message.text  # type: ignore
        if text == _(BEAUTIFY):
            return self.beautify_image_processor.process_file(update, context)
        if text == _(TO_PDF):
            return self.image_to_pdf_processor.process_file(update, context)
        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)

        return WAIT_IMAGE_TASK
