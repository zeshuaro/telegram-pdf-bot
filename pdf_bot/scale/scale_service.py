from telegram import ParseMode, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService, ScaleData
from pdf_bot.pdf.models import ScaleByData, ScaleToData
from pdf_bot.scale import scale_constants
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class ScaleService:
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
    def ask_scale_type(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        keyboard = [
            [_(scale_constants.BY_SCALING_FACTOR), _(scale_constants.TO_DIMENSION)],
            [_(BACK)],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        update.effective_message.reply_text(
            _("Select the scale type that you'll like to perform"),
            reply_markup=reply_markup,
        )

        return scale_constants.WAIT_SCALE_TYPE

    def check_scale_type(self, update, context):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text in {
            _(scale_constants.BY_SCALING_FACTOR),
            _(scale_constants.TO_DIMENSION),
        }:
            return self._ask_scale_value(update, context)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)
        return scale_constants.WAIT_SCALE_TYPE

    def scale_pdf_by_factor(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message
        text = message.text

        if text == _(BACK):
            return self.ask_scale_type(update, context)

        try:
            scale_data = ScaleByData.from_string(text)
        except ValueError:
            message.reply_text(
                _("The scaling factors {values} are invalid, please try again").format(
                    values=f"<b>{text}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
            return scale_constants.WAIT_SCALE_FACTOR
        return self._scale_pdf(update, context, scale_data)

    def scale_pdf_to_dimension(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message
        text = message.text

        if message.text == _(BACK):
            return self.ask_scale_type(update, context)

        try:
            scale_data = ScaleToData.from_string(text)
        except ValueError:
            message.reply_text(
                _("The dimensions {values} are invalid, please try again").format(
                    values=f"<b>{text}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
            return scale_constants.WAIT_SCALE_DIMENSION
        return self._scale_pdf(update, context, scale_data)

    @staticmethod
    def _ask_scale_value(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK)]], one_time_keyboard=True, resize_keyboard=True
        )

        if message.text == _(scale_constants.BY_SCALING_FACTOR):
            message.reply_text(
                "{desc_1}\n{desc_2}\n\n{desc_3}".format(
                    desc_1=_(
                        "Send me the scaling factors for the horizontal "
                        "and vertical axes"
                    ),
                    desc_2=f"<b>{_('Example: 2 0.5')}</b>",
                    desc_3=_(
                        "This will double the horizontal axis "
                        "and halve the vertical axis"
                    ),
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return scale_constants.WAIT_SCALE_FACTOR

        message.reply_text(
            "{desc_1}\n{desc_2}\n\n{desc_3}".format(
                desc_1=_("Send me the width and height"),
                desc_2=f"<b>{_('Example: 150 200')}</b>",
                desc_3=_("This will set the width to 150 and height to 200"),
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
        return scale_constants.WAIT_SCALE_DIMENSION

    def _scale_pdf(
        self, update: Update, context: CallbackContext, scale_data: ScaleData
    ):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.scale_pdf(file_id, scale_data) as out_path:
            send_result_file(update, context, out_path, TaskType.scale_pdf)
        return ConversationHandler.END
