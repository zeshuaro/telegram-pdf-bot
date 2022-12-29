from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData

from .abstract_pdf_select_and_text_processor import (
    AbstractPdfSelectAndTextProcessor,
    OptionAndInputData,
    SelectOption,
)


class CropType(SelectOption):
    by_percentage = _("By percentage")
    by_margin_size = _("To margin size")

    @property
    def ask_value_text(self) -> str:  # pragma: no cover
        match self:
            case CropType.by_percentage:
                return _(
                    "Send me a number between 0 and 100\n\nThis is the percentage of"
                    " margin space to retain between the content in your PDF file and"
                    " the page"
                )
            case CropType.by_margin_size:
                return _(
                    "Send me a number that you'll like to adjust the margin"
                    " size\n\nPositive numbers will decrease the margin size and"
                    " negative numbers will increase it"
                )


class CropPdfData(FileData):
    ...


class CropOptionAndInputData(OptionAndInputData):
    text: float


class CropPdfProcessor(AbstractPdfSelectAndTextProcessor):
    @property
    def entry_point_data_type(self) -> type[CropPdfData]:
        return CropPdfData

    @property
    def task_type(self) -> TaskType:
        return TaskType.crop_pdf

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Crop"), self.entry_point_data_type)

    @property
    def ask_select_option_text(self) -> str:  # pragma: no cover
        return _("Select the crop type you'll like to perform")

    @property
    def select_option_type(self) -> type[CropType]:
        return CropType

    @property
    def invalid_text_input_error(self) -> str:  # pragma: no cover
        return _("The crop values are invalid, try again")

    @property
    def option_and_input_data_type(self) -> type[CropOptionAndInputData]:
        return CropOptionAndInputData

    def get_cleaned_text_input(self, text: str) -> float | None:
        try:
            return float(text)
        except ValueError:
            return None

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData
    ) -> AsyncGenerator[FileTaskResult, None]:
        if not isinstance(file_data, CropOptionAndInputData):
            raise TypeError(f"Invalid file data type: {type(file_data)}")

        match file_data.option:
            case CropType.by_percentage:
                async with self.pdf_service.crop_pdf_by_percentage(
                    file_data.id, file_data.text
                ) as path:
                    yield FileTaskResult(path)
            case CropType.by_margin_size:
                async with self.pdf_service.crop_pdf_by_margin_size(
                    file_data.id, file_data.text
                ) as path:
                    yield FileTaskResult(path)
            case _:
                raise ValueError(f"Invalid file data option: {file_data.option}")
