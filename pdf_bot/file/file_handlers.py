from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import (
    BACK,
    BEAUTIFY,
    BLACK_AND_WHITE,
    CANCEL,
    COMPRESS,
    COMPRESSED,
    CROP,
    DECRYPT,
    ENCRYPT,
    EXTRACT_IMAGE,
    EXTRACT_TEXT,
    IMAGES,
    OCR,
    PDF_INFO,
    PREVIEW,
    RENAME,
    ROTATE,
    SCALE,
    SPLIT,
    TEXT_FILTER,
    TO_IMAGES,
    TO_PDF,
    WAIT_EXTRACT_IMAGE_TYPE,
    WAIT_IMAGE_TASK,
    WAIT_TO_IMAGE_TYPE,
)
from pdf_bot.crop import CropService
from pdf_bot.file.file_service import FileService
from pdf_bot.file_task import FileTaskService
from pdf_bot.files.image import (
    ask_image_results_type,
    ask_image_task,
    get_pdf_images,
    pdf_to_images,
    process_image_task,
)
from pdf_bot.language import set_lang
from pdf_bot.pdf_processor import (
    DecryptPDFProcessor,
    EncryptPDFProcessor,
    GrayscalePDFProcessor,
    PreviewPDFProcessor,
    RenamePDFProcessor,
    RotatePDFProcessor,
    ScalePDFProcessor,
    SplitPDFProcessor,
)
from pdf_bot.text import ExtractTextService, OCRService
from pdf_bot.utils import cancel


class FileHandlers:
    def __init__(
        self,
        file_task_service: FileTaskService,
        file_service: FileService,
        crop_service: CropService,
        decrypt_pdf_processor: DecryptPDFProcessor,
        encrypt_pdf_processor: EncryptPDFProcessor,
        extract_text_service: ExtractTextService,
        grayscale_pdf_processor: GrayscalePDFProcessor,
        ocr_service: OCRService,
        preview_pdf_processor: PreviewPDFProcessor,
        rename_pdf_processor: RenamePDFProcessor,
        rotate_pdf_processor: RotatePDFProcessor,
        scale_pdf_processor: ScalePDFProcessor,
        split_pdf_processor: SplitPDFProcessor,
    ) -> None:
        self.file_task_service = file_task_service
        self.file_service = file_service
        self.crop_service = crop_service
        self.decrypt_pdf_processor = decrypt_pdf_processor
        self.encrypt_pdf_processor = encrypt_pdf_processor
        self.extract_text_service = extract_text_service
        self.grayscale_pdf_processor = grayscale_pdf_processor
        self.ocr_service = ocr_service
        self.preview_pdf_processor = preview_pdf_processor
        self.rename_pdf_processor = rename_pdf_processor
        self.rotate_pdf_processor = rotate_pdf_processor
        self.scale_pdf_processor = scale_pdf_processor
        self.split_pdf_processor = split_pdf_processor

    def conversation_handler(self):
        return ConversationHandler(
            entry_points=[
                MessageHandler(Filters.document, self.check_doc),
                MessageHandler(Filters.photo, self.check_image),
            ],
            states={
                FileTaskService.WAIT_PDF_TASK: [
                    MessageHandler(TEXT_FILTER, self.check_doc_task)
                ],
                WAIT_IMAGE_TASK: [MessageHandler(TEXT_FILTER, self.check_image_task)],
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
                WAIT_EXTRACT_IMAGE_TYPE: [
                    MessageHandler(TEXT_FILTER, self.check_get_images_task)
                ],
                WAIT_TO_IMAGE_TYPE: [
                    MessageHandler(TEXT_FILTER, self.check_to_images_task)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            allow_reentry=True,
            run_async=True,
        )

    def check_doc(self, update, context):
        doc = update.effective_message.document
        if doc.mime_type.startswith("image"):
            return ask_image_task(update, context, doc)
        if not doc.mime_type.endswith("pdf"):
            return ConversationHandler.END
        if doc.file_size >= MAX_FILESIZE_DOWNLOAD:
            _ = set_lang(update, context)
            update.effective_message.reply_text(
                "{desc_1}\n\n{desc_2}".format(
                    desc_1=_("Your file is too big for me to download and process"),
                    desc_2=_(
                        "Note that this is a Telegram Bot limitation and there's "
                        "nothing I can do unless Telegram changes this limit"
                    ),
                ),
            )

            return ConversationHandler.END

        context.user_data[PDF_INFO] = doc.file_id, doc.file_name
        return self.file_task_service.ask_pdf_task(update, context)

    @staticmethod
    def check_image(update, context):
        return ask_image_task(update, context, update.effective_message.photo[-1])

    def check_doc_task(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text == _(CROP):
            return self.crop_service.ask_crop_type(update, context)
        if text == _(DECRYPT):
            return self.decrypt_pdf_processor.ask_password(update, context)
        if text == _(ENCRYPT):
            return self.encrypt_pdf_processor.ask_password(update, context)
        if text in [_(EXTRACT_IMAGE), _(TO_IMAGES)]:
            return ask_image_results_type(update, context)
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
            return self.extract_text_service.process_file(update, context)
        if text == OCR:
            return self.ocr_service.process_file(update, context)
        if text == _(COMPRESS):
            return self.file_service.compress_pdf(update, context)
        if text == _(BLACK_AND_WHITE):
            return self.grayscale_pdf_processor.process_file(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return FileTaskService.WAIT_PDF_TASK

    @staticmethod
    def check_image_task(update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in [_(BEAUTIFY), _(TO_PDF)]:
            return process_image_task(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return WAIT_IMAGE_TASK

    def check_get_images_task(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in [_(IMAGES), _(COMPRESSED)]:
            return get_pdf_images(update, context)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        return WAIT_EXTRACT_IMAGE_TYPE

    def check_to_images_task(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in [_(IMAGES), _(COMPRESSED)]:
            return pdf_to_images(update, context)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        return WAIT_TO_IMAGE_TYPE
