from contextlib import contextmanager
from gettext import gettext as _
from typing import Generator

from telegram import ParseMode, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK
from pdf_bot.pdf import ScaleData
from pdf_bot.pdf.models import ScaleByData, ScaleToData

from .abstract_pdf_processor import AbstractPDFProcessor


class ScalePDFProcessor(AbstractPDFProcessor):
    BY_SCALING_FACTOR = _("By scaling factor")
    TO_DIMENSION = _("To dimension")

    WAIT_SCALE_TYPE = "wait_scale_type"
    WAIT_SCALE_FACTOR = "wait_scale_factor"
    WAIT_SCALE_DIMENSION = "wait_scale_dimension"

    @property
    def task_type(self) -> TaskType:
        return TaskType.scale_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @contextmanager
    def process_file_task(
        self, file_id: str, message_text: str
    ) -> Generator[str, None, None]:
        scale_data = ScaleData.from_string(message_text)
        with self.pdf_service.scale_pdf(file_id, scale_data) as path:
            yield path

    def ask_scale_type(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [_(self.BY_SCALING_FACTOR), _(self.TO_DIMENSION)],
            [_(BACK)],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        update.effective_message.reply_text(
            _("Select the scale type that you'll like to perform"),
            reply_markup=reply_markup,
        )

        return self.WAIT_SCALE_TYPE

    def check_scale_type(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        text = update.effective_message.text

        if text in {
            _(self.BY_SCALING_FACTOR),
            _(self.TO_DIMENSION),
        }:
            return self._ask_scale_value(update, context)
        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)
        return self.WAIT_SCALE_TYPE

    def scale_pdf_by_factor(
        self, update: Update, context: CallbackContext
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message
        text = message.text

        if text == _(BACK):
            return self.ask_scale_type(update, context)

        try:
            ScaleByData.from_string(text)
        except ValueError:
            message.reply_text(
                _("The scaling factors {values} are invalid, please try again").format(
                    values=f"<b>{text}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
            return self.WAIT_SCALE_FACTOR

        self.process_file(update, context)
        return ConversationHandler.END

    def scale_pdf_to_dimension(
        self, update: Update, context: CallbackContext
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message
        text = message.text

        if message.text == _(BACK):
            return self.ask_scale_type(update, context)

        try:
            ScaleToData.from_string(text)
        except ValueError:
            message.reply_text(
                _("The dimensions {values} are invalid, please try again").format(
                    values=f"<b>{text}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
            return self.WAIT_SCALE_DIMENSION

        self.process_file(update, context)
        return ConversationHandler.END

    def _ask_scale_value(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        if update.effective_message.text == _(self.BY_SCALING_FACTOR):
            self.telegram_service.reply_with_back_markup(
                update,
                context,
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
                parse_mode=ParseMode.HTML,
            )
            return self.WAIT_SCALE_FACTOR

        self.telegram_service.reply_with_back_markup(
            update,
            context,
            "{desc_1}\n{desc_2}\n\n{desc_3}".format(
                desc_1=_("Send me the width and height"),
                desc_2=f"<b>{_('Example: 150 200')}</b>",
                desc_3=_("This will set the width to 150 and height to 200"),
            ),
            parse_mode=ParseMode.HTML,
        )
        return self.WAIT_SCALE_DIMENSION
