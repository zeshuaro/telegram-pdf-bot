import re
from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator, Callable

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_pdf_text_input_processor import (
    AbstractPdfTextInputProcessor,
    TextInputData,
)


class RenamePdfData(FileData):
    pass


class RenamePdfProcessor(AbstractPdfTextInputProcessor):
    INVALID_CHARACTERS = r"\/*?:\'<>|"

    @property
    def task_type(self) -> TaskType:
        return TaskType.rename_pdf

    @property
    def entry_point_data_type(self) -> type[RenamePdfData]:
        return RenamePdfData

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Rename"), self.entry_point_data_type)

    @property
    def invalid_text_input_error(self) -> str:  # pragma: no cover
        return _(
            "File names can't contain any of the following characters, please try"
            " again:\n{invalid_chars}".format(invalid_chars=self.INVALID_CHARACTERS)
        )

    def get_ask_text_input_text(
        self, _: Callable[[str], str]
    ) -> str:  # pragma: no cover
        return _("Send me the file name that you'll like to rename your PDF file into")

    def get_cleaned_text_input(self, text: str) -> str | None:
        cleaned_text = re.sub(r"\.pdf$", "", text)
        if set(cleaned_text) & set(self.INVALID_CHARACTERS):
            return None
        return f"{cleaned_text}.pdf"

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        if not isinstance(file_data, TextInputData):
            raise TypeError(f"Invalid file data: {type(file_data)}")

        async with self.pdf_service.rename_pdf(file_data.id, file_data.text) as path:
            yield path
