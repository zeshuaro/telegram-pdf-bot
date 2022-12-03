from contextlib import contextmanager
from typing import Generator

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK

from .abstract_pdf_processor import AbstractPDFProcessor


class RotatePDFProcessor(AbstractPDFProcessor):
    WAIT_ROTATE_DEGREE = "wait_rotate_degree"
    _ROTATE_90 = "90"
    _ROTATE_180 = "180"
    _ROTATE_270 = "270"

    @property
    def task_type(self) -> TaskType:
        return TaskType.rotate_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @contextmanager
    def process_file_task(
        self, file_id: str, message_text: str
    ) -> Generator[str, None, None]:
        with self.pdf_service.rotate_pdf(file_id, int(message_text)) as path:
            yield path

    def ask_degree(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)

        keyboard = [
            [self._ROTATE_90, self._ROTATE_180],
            [self._ROTATE_270, _(BACK)],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _(
                "Select the degrees that you'll like to "
                "rotate your PDF file in clockwise"
            ),
            reply_markup=reply_markup,
        )

        return self.WAIT_ROTATE_DEGREE

    def rotate_pdf(self, update: Update, context: CallbackContext) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message
        text = message.text

        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)
        if text not in {
            self._ROTATE_90,
            self._ROTATE_180,
            self._ROTATE_270,
        }:
            message.reply_text(_("Invalid rotation degree, try again"))
            return self.WAIT_ROTATE_DEGREE

        return self.process_file(update, context)
