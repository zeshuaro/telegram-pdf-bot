import re
from contextlib import contextmanager
from typing import Generator

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK
from pdf_bot.file_processor import AbstractFileProcessor


class RenamePDFProcessor(AbstractFileProcessor):
    WAIT_NEW_FILE_NAME = "wait_new_file_name"
    INVALID_CHARACTERS = r"\/*?:\'<>|"

    @property
    def task_type(self) -> TaskType:
        return TaskType.rename_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @contextmanager
    def process_file_task(
        self, file_id: str, message_text: str
    ) -> Generator[str, None, None]:
        file_name = re.sub(r"\.pdf$", "", message_text)
        with self.pdf_service.rename_pdf(file_id, f"{file_name}.pdf") as path:
            yield path

    def ask_new_file_name(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_back_markup(
            update,
            context,
            _("Send me the file name that you'll like to rename your PDF file into"),
        )
        return self.WAIT_NEW_FILE_NAME

    def rename_pdf(self, update: Update, context: CallbackContext) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        text = re.sub(r"\.pdf$", "", message.text)
        if set(text) & set(self.INVALID_CHARACTERS):
            message.reply_text(
                "{desc_1}\n{invalid_chars}\n{desc_2}".format(
                    desc_1=_(
                        "File names can't contain any of the following characters:"
                    ),
                    invalid_chars=self.INVALID_CHARACTERS,
                    desc_2=_("Please try again"),
                ),
            )
            return self.WAIT_NEW_FILE_NAME

        return self.process_file(update, context)
