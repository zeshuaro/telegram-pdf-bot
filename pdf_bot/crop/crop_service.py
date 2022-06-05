from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.crop import crop_constants
from pdf_bot.file_task import FileTaskService
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class CropService:
    def __init__(
        self,
        file_task_service: FileTaskService,
        pdf_service: PdfService,
        telegram_service: TelegramService,
    ) -> None:
        self.file_task_service = file_task_service
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_crop_type(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        keyboard = [
            [_(crop_constants.BY_PERCENTAGE), _(crop_constants.BY_MARGIN_SIZE)],
            [_(BACK)],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        update.effective_message.reply_text(
            _("Select the crop type that you'll like to perform"),
            reply_markup=reply_markup,
        )

        return crop_constants.WAIT_CROP_TYPE

    def check_crop_type(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in [_(crop_constants.BY_PERCENTAGE), _(crop_constants.BY_MARGIN_SIZE)]:
            return self.ask_crop_value(update, context)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)
        return crop_constants.WAIT_CROP_TYPE

    @staticmethod
    def ask_crop_value(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK)]], one_time_keyboard=True, resize_keyboard=True
        )

        if message.text == _(crop_constants.BY_PERCENTAGE):
            message.reply_text(
                "{desc_1}\n\n{desc_2}".format(
                    desc_1=_(
                        "Send me a number between {min_percent} and {max_percent}"
                    ).format(
                        min_percent=crop_constants.MIN_PERCENTAGE,
                        max_percent=crop_constants.MAX_PERCENTAGE,
                    ),
                    desc_2=_(
                        "This is the percentage of margin space to retain "
                        "between the content in your PDF file and the page"
                    ),
                ),
                reply_markup=reply_markup,
            )
            return crop_constants.WAIT_CROP_PERCENTAGE

        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Send me a number that you'll like to adjust the margin size"),
                desc_2=_(
                    "Positive numbers will decrease the margin size "
                    "and negative numbers will increase it"
                ),
            ),
            reply_markup=reply_markup,
        )
        return crop_constants.WAIT_CROP_MARGIN_SIZE

    def crop_pdf_by_percentage(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.ask_crop_type(update, context)

        try:
            percent = float(message.text)
        except ValueError:
            message.reply_text(
                _(
                    "The number {number} is not between "
                    "{min_percent} and {max_percent}, please try again"
                ).format(
                    number=message.text,
                    min_percent=crop_constants.MIN_PERCENTAGE,
                    max_percent=crop_constants.MAX_PERCENTAGE,
                ),
            )
            return crop_constants.WAIT_CROP_PERCENTAGE

        return self._crop_pdf(update, context, percentage=percent)

    def crop_pdf_by_margin_size(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.ask_crop_type(update, context)

        try:
            margin_size = float(message.text)
        except ValueError:
            _ = set_lang(update, context)
            message.reply_text(
                _("The number {number} is invalid, please try again").format(
                    number=message.text
                )
            )
            return crop_constants.WAIT_CROP_MARGIN_SIZE

        return self._crop_pdf(update, context, margin_size=margin_size)

    def _crop_pdf(
        self,
        update: Update,
        context: CallbackContext,
        percentage: float | None = None,
        margin_size: float | None = None,
    ):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.crop_pdf(
            file_id, percentage=percentage, margin_size=margin_size
        ) as out_path:
            send_result_file(update, context, out_path, TaskType.crop_pdf)
        return ConversationHandler.END
