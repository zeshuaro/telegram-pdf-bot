from typing import List

from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BEAUTIFY, CANCEL, REMOVE_LAST, TO_PDF
from pdf_bot.image.constants import IMAGE_DATA, WAIT_IMAGE
from pdf_bot.language import set_lang
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError
from pdf_bot.utils import cancel, reply_with_cancel_btn, send_result_file


class ImageService:
    def __init__(
        self, pdf_service: PdfService, telegram_service: TelegramService
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_first_image(update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        context.user_data[IMAGE_DATA] = []

        reply_with_cancel_btn(
            update,
            context,
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_(
                    "Send me the images that you'll like to beautify "
                    "or convert into a PDF file"
                ),
                desc_2=_(
                    "Note that the images will be beautified "
                    "and converted in the order that you send me"
                ),
            ),
        )

        return WAIT_IMAGE

    def check_image(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            img_file = self.telegram_service.check_image(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return WAIT_IMAGE

        try:
            file_name = img_file.file_name
        except AttributeError:
            file_name = _("File name unavailable")

        context.user_data[IMAGE_DATA].append(FileData(img_file.file_id, file_name))
        return self._ask_next_image(update, context)

    def check_text(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        message = update.effective_message
        text = message.text

        if text in [_(REMOVE_LAST), _(BEAUTIFY), _(TO_PDF)]:
            try:
                file_data_list = self.telegram_service.get_user_data(
                    context, IMAGE_DATA
                )
            except TelegramServiceError as e:
                message.reply_text(_(str(e)))
                return ConversationHandler.END

            if text == _(REMOVE_LAST):
                return self._remove_last_image(update, context, file_data_list)
            if text in [_(BEAUTIFY), _(TO_PDF)]:
                return self._process_images(update, context, file_data_list)
        elif text == _(CANCEL):
            return cancel(update, context)

        return WAIT_IMAGE

    def _ask_next_image(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        message = update.effective_message
        text = "{desc}\n".format(desc=_("You've sent me these images so far:"))
        self.telegram_service.send_file_names(
            message.chat_id, text, context.user_data[IMAGE_DATA]
        )

        reply_markup = ReplyKeyboardMarkup(
            [[_(BEAUTIFY), _(TO_PDF)], [_(REMOVE_LAST), _(CANCEL)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        message.reply_text(
            _(
                "Select the task from below if you've sent me all the images, or keep "
                "sending me the images"
            ),
            reply_markup=reply_markup,
        )

        return WAIT_IMAGE

    def _remove_last_image(
        self, update: Update, context: CallbackContext, file_data_list: List[FileData]
    ) -> int:
        _ = set_lang(update, context)
        try:
            file_data = file_data_list.pop()
        except IndexError:
            update.effective_message.reply_text(
                _("You've already removed all the images you've sent me")
            )
            return self.ask_first_image(update, context)

        update.effective_message.reply_text(
            _("{file_name} has been removed for beautifying or converting").format(
                file_name=f"<b>{file_data.name}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )

        if file_data_list:
            context.user_data[IMAGE_DATA] = file_data_list
            return self._ask_next_image(update, context)
        return self.ask_first_image(update, context)

    def _process_images(
        self, update: Update, context: CallbackContext, file_data_list: List[FileData]
    ) -> int:
        _ = set_lang(update, context)
        if update.effective_message.text == _(BEAUTIFY):
            return self._beautify_images(update, context, file_data_list)
        return self._convert_images(update, context, file_data_list)

    def _beautify_images(
        self, update: Update, context: CallbackContext, file_data_list: List[FileData]
    ) -> int:
        _ = set_lang(update, context)
        message = update.effective_message

        message.reply_text(
            _("Beautifying and converting your images into a PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            with self.pdf_service.beautify_images(file_data_list) as out_path:
                send_result_file(update, context, out_path, TaskType.beautify_image)
        except PdfServiceError as e:
            message.reply_text(_(str(e)))

        return ConversationHandler.END

    def _convert_images(
        self, update: Update, context: CallbackContext, file_data_list: List[FileData]
    ) -> int:
        _ = set_lang(update, context)
        message = update.effective_message

        message.reply_text(
            _("Converting your images into a PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            with self.pdf_service.convert_images_to_pdf(file_data_list) as out_path:
                send_result_file(update, context, out_path, TaskType.image_to_pdf)
        except PdfServiceError as e:
            message.reply_text(_(str(e)))

        return ConversationHandler.END
