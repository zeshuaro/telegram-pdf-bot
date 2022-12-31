from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.pdf import ScaleData

from .abstract_pdf_select_and_text_processor import (
    AbstractPdfSelectAndTextProcessor,
    OptionAndInputData,
    SelectOption,
)


class ScaleType(SelectOption):
    by_factor = _("By factor")
    to_dimension = _("To dimension")

    @property
    def ask_value_text(self) -> str:  # pragma: no cover
        match self:
            case ScaleType.by_factor:
                return _(
                    "Send me the scaling factors for the horizontal and vertical"
                    " axes\n\nExample: 2 0.5 - this will double the horizontal axis and"
                    " halve the vertical axis"
                )
            case ScaleType.to_dimension:
                return _(
                    "Send me the width and height\n\nExample: 150 200 - this will set"
                    " the width to 150 and height to 200"
                )


class ScalePdfData(FileData):
    ...


class ScaleOptionAndInputData(OptionAndInputData):
    text: ScaleData


class ScalePdfProcessor(AbstractPdfSelectAndTextProcessor):
    @property
    def entry_point_data_type(self) -> type[ScalePdfData]:
        return ScalePdfData

    @property
    def task_type(self) -> TaskType:
        return TaskType.scale_pdf

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Scale"), self.entry_point_data_type)

    @property
    def ask_select_option_text(self) -> str:  # pragma: no cover
        return _("Select the scale type you'll like to perform")

    @property
    def select_option_type(self) -> type[ScaleType]:
        return ScaleType

    @property
    def invalid_text_input_error(self) -> str:  # pragma: no cover
        return _("The scale values are invalid, try again")

    @property
    def option_and_input_data_type(self) -> type[ScaleOptionAndInputData]:
        return ScaleOptionAndInputData

    def get_cleaned_text_input(self, text: str) -> ScaleData | None:
        try:
            return ScaleData.from_string(text)
        except ValueError:
            return None

    @asynccontextmanager
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        if not isinstance(file_data, ScaleOptionAndInputData):
            raise TypeError(f"Invalid file data type: {type(file_data)}")

        match file_data.option:
            case ScaleType.by_factor:
                async with self.pdf_service.scale_pdf_by_factor(
                    file_data.id, file_data.text
                ) as path:
                    yield FileTaskResult(path)
            case ScaleType.to_dimension:
                async with self.pdf_service.scale_pdf_to_dimension(
                    file_data.id, file_data.text
                ) as path:
                    yield FileTaskResult(path)
            case _:
                raise ValueError(f"Invalid file data option: {file_data.option}")
