from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import (
    BACK,
    BEAUTIFY,
    BLACK_AND_WHITE,
    BY_PERCENT,
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
    TEXT_FILE,
    TEXT_FILTER,
    TEXT_MESSAGE,
    TO_DIMENSIONS,
    TO_IMAGES,
    TO_PDF,
    WAIT_EXTRACT_IMAGE_TYPE,
    WAIT_IMAGE_TASK,
    WAIT_ROTATE_DEGREE,
    WAIT_SCALE_DIMENSION,
    WAIT_SCALE_PERCENT,
    WAIT_SCALE_TYPE,
    WAIT_SPLIT_RANGE,
    WAIT_TEXT_TYPE,
    WAIT_TO_IMAGE_TYPE,
)
from pdf_bot.crop import CropService, crop_constants
from pdf_bot.decrypt import DecryptService, decrypt_constants
from pdf_bot.encrypt import EncryptService, encrypt_constants
from pdf_bot.file.file_service import FileService
from pdf_bot.file_task import FileTaskService, file_task_constants
from pdf_bot.files.image import (
    ask_image_results_type,
    ask_image_task,
    get_pdf_images,
    get_pdf_preview,
    pdf_to_images,
    process_image_task,
)
from pdf_bot.files.rotate import ask_rotate_degree, check_rotate_degree
from pdf_bot.files.scale import (
    ask_scale_type,
    ask_scale_value,
    check_scale_dimension,
    check_scale_percent,
)
from pdf_bot.files.split import ask_split_range, split_pdf
from pdf_bot.files.text import ask_text_type, get_pdf_text
from pdf_bot.language import set_lang
from pdf_bot.rename import RenameService, rename_constants
from pdf_bot.utils import cancel


class FileHandlers:
    def __init__(
        self,
        file_task_service: FileTaskService,
        file_service: FileService,
        crop_service: CropService,
        decrypt_service: DecryptService,
        encrypt_service: EncryptService,
        rename_service: RenameService,
    ) -> None:
        self.file_task_service = file_task_service
        self.file_service = file_service
        self.crop_service = crop_service
        self.decrypt_service = decrypt_service
        self.encrypt_service = encrypt_service
        self.rename_service = rename_service

    def conversation_handler(self):
        return ConversationHandler(
            entry_points=[
                MessageHandler(Filters.document, self.check_doc),
                MessageHandler(Filters.photo, self.check_image),
            ],
            states={
                file_task_constants.WAIT_PDF_TASK: [
                    MessageHandler(TEXT_FILTER, self.check_doc_task)
                ],
                WAIT_IMAGE_TASK: [MessageHandler(TEXT_FILTER, self.check_image_task)],
                crop_constants.WAIT_CROP_TYPE: [
                    MessageHandler(TEXT_FILTER, self.crop_service.check_crop_type)
                ],
                crop_constants.WAIT_CROP_PERCENTAGE: [
                    MessageHandler(
                        TEXT_FILTER, self.crop_service.crop_pdf_by_percentage
                    )
                ],
                crop_constants.WAIT_CROP_MARGIN_SIZE: [
                    MessageHandler(
                        TEXT_FILTER, self.crop_service.crop_pdf_by_margin_size
                    )
                ],
                decrypt_constants.WAIT_DECRYPT_PASSWORD: [
                    MessageHandler(TEXT_FILTER, self.decrypt_service.decrypt_pdf)
                ],
                encrypt_constants.WAIT_ENCRYPT_PASSWORD: [
                    MessageHandler(TEXT_FILTER, self.encrypt_service.encrypt_pdf)
                ],
                rename_constants.WAIT_NEW_FILE_NAME: [
                    MessageHandler(TEXT_FILTER, self.rename_service.rename_pdf)
                ],
                WAIT_ROTATE_DEGREE: [MessageHandler(TEXT_FILTER, check_rotate_degree)],
                WAIT_SPLIT_RANGE: [MessageHandler(TEXT_FILTER, split_pdf)],
                WAIT_TEXT_TYPE: [MessageHandler(TEXT_FILTER, self.check_text_task)],
                WAIT_SCALE_TYPE: [MessageHandler(TEXT_FILTER, self.check_scale_task)],
                WAIT_SCALE_PERCENT: [MessageHandler(TEXT_FILTER, check_scale_percent)],
                WAIT_SCALE_DIMENSION: [
                    MessageHandler(TEXT_FILTER, check_scale_dimension)
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
            return self.decrypt_service.ask_password(update, context)
        if text == _(ENCRYPT):
            return self.encrypt_service.ask_password(update, context)
        if text in [_(EXTRACT_IMAGE), _(TO_IMAGES)]:
            return ask_image_results_type(update, context)
        if text == _(PREVIEW):
            return get_pdf_preview(update, context)
        if text == _(RENAME):
            return self.rename_service.ask_new_file_name(update, context)
        if text == _(ROTATE):
            return ask_rotate_degree(update, context)
        if text in [_(SCALE)]:
            return ask_scale_type(update, context)
        if text == _(SPLIT):
            return ask_split_range(update, context)
        if text == _(EXTRACT_TEXT):
            return ask_text_type(update, context)
        if text == OCR:
            return self.file_service.ocr_pdf(update, context)
        if text == _(COMPRESS):
            return self.file_service.compress_pdf(update, context)
        if text == _(BLACK_AND_WHITE):
            return self.file_service.black_and_white_pdf(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return file_task_constants.WAIT_PDF_TASK

    @staticmethod
    def check_image_task(update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in [_(BEAUTIFY), _(TO_PDF)]:
            return process_image_task(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return WAIT_IMAGE_TASK

    def check_scale_task(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in [_(BY_PERCENT), _(TO_DIMENSIONS)]:
            return ask_scale_value(update, context)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        return WAIT_SCALE_TYPE

    def check_text_task(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text == _(TEXT_MESSAGE):
            return get_pdf_text(update, context, is_file=False)
        if text == _(TEXT_FILE):
            return get_pdf_text(update, context, is_file=True)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        return WAIT_TEXT_TYPE

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
