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
from pdf_bot.decrypt import DecryptService
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
from pdf_bot.language import set_lang
from pdf_bot.rename import RenameService, rename_constants
from pdf_bot.rotate import RotateService, rotate_constants
from pdf_bot.scale import ScaleService, scale_constants
from pdf_bot.split import SplitService, split_constants
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
        rotate_service: RotateService,
        scale_service: ScaleService,
        split_service: SplitService,
    ) -> None:
        self.file_task_service = file_task_service
        self.file_service = file_service
        self.crop_service = crop_service
        self.decrypt_service = decrypt_service
        self.encrypt_service = encrypt_service
        self.rename_service = rename_service
        self.rotate_service = rotate_service
        self.scale_service = scale_service
        self.split_service = split_service

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
                DecryptService.WAIT_DECRYPT_PASSWORD: [
                    MessageHandler(TEXT_FILTER, self.decrypt_service.decrypt_pdf)
                ],
                encrypt_constants.WAIT_ENCRYPT_PASSWORD: [
                    MessageHandler(TEXT_FILTER, self.encrypt_service.encrypt_pdf)
                ],
                rename_constants.WAIT_NEW_FILE_NAME: [
                    MessageHandler(TEXT_FILTER, self.rename_service.rename_pdf)
                ],
                rotate_constants.WAIT_ROTATE_DEGREE: [
                    MessageHandler(TEXT_FILTER, self.rotate_service.rotate_pdf)
                ],
                scale_constants.WAIT_SCALE_TYPE: [
                    MessageHandler(TEXT_FILTER, self.scale_service.check_scale_type)
                ],
                scale_constants.WAIT_SCALE_FACTOR: [
                    MessageHandler(TEXT_FILTER, self.scale_service.scale_pdf_by_factor)
                ],
                scale_constants.WAIT_SCALE_DIMENSION: [
                    MessageHandler(
                        TEXT_FILTER, self.scale_service.scale_pdf_to_dimension
                    )
                ],
                split_constants.WAIT_SPLIT_RANGE: [
                    MessageHandler(TEXT_FILTER, self.split_service.split_pdf)
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
            return self.rotate_service.ask_degree(update, context)
        if text == _(SCALE):
            return self.scale_service.ask_scale_type(update, context)
        if text == _(SPLIT):
            return self.split_service.ask_split_range(update, context)
        if text == _(EXTRACT_TEXT):
            return self.file_service.extract_text_from_pdf(update, context)
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
