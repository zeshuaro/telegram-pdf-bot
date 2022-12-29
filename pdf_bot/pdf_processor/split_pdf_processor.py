from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator, Callable

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_pdf_text_input_processor import (
    AbstractPdfTextInputProcessor,
    TextInputData,
)


class SplitPdfData(FileData):
    pass


class SplitPdfProcessor(AbstractPdfTextInputProcessor):
    WAIT_SPLIT_RANGE = "wait_split_range"

    @property
    def task_type(self) -> TaskType:
        return TaskType.split_pdf

    @property
    def entry_point_data_type(self) -> type[SplitPdfData]:
        return SplitPdfData

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Split"), self.entry_point_data_type)

    @property
    def invalid_text_input_error(self) -> str:  # pragma: no cover
        return _("The split range is invalid, please try again")

    def get_ask_text_input_text(
        self, _: Callable[[str], str]
    ) -> str:  # pragma: no cover
        return (
            "{intro}\n\n"
            "<b>{general}</b>\n"
            "<code>{all}</code>\n"
            "<code>{eight_only}</code>\n"
            "<code>{first_three}</code>\n"
            "<code>{from_eight}</code>\n"
            "<code>{last_only}</code>\n"
            "<code>{all_except_last}</code>\n"
            "<code>{second_last}</code>\n"
            "<code>{last_two}</code>\n"
            "<code>{third_second}</code>\n\n"
            "<b>{advanced}</b>\n"
            "<code>{pages_to_end}</code>\n"
            "<code>{odd_pages}</code>\n"
            "<code>{all_reversed}</code>\n"
            "<code>{pages_except}</code>\n"
            "<code>{pages_reverse_from}</code>"
        ).format(
            intro=_("Send me the range of pages that you'll like to keep"),
            general=_("General usage"),
            all=_("{range}      all pages").format(range=":"),
            eight_only=_("{range}      page 8 only").format(range="7"),
            first_three=_("{range}    first three pages").format(range="0:3"),
            from_eight=_("{range}     from page 8 onward").format(range="7:"),
            last_only=_("{range}     last page only").format(range="-1"),
            all_except_last=_("{range}    all pages except the last page").format(
                range=":-1"
            ),
            second_last=_("{range}     second last page only").format(range="-2"),
            last_two=_("{range}    last two pages").format(range="-2:"),
            third_second=_("{range}  third and second last pages").format(
                range="-3:-1"
            ),
            advanced=_("Advanced usage"),
            pages_to_end=_("{range}    pages {pages} and to the end").format(
                range="::2", pages="0 2 4 ..."
            ),
            odd_pages=_("{range} pages {pages}").format(
                range="1:10:2", pages="1 3 5 7 9"
            ),
            all_reversed=_("{range}   all pages in reversed order").format(
                range="::-1"
            ),
            pages_except=_("{range} pages {pages} except {page}").format(
                range="3:0:-1", pages="3 2 1", page="0"
            ),
            pages_reverse_from=_("{range}  pages {pages}").format(
                range="2::-1", pages="2 1 0"
            ),
        )

    def get_cleaned_text_input(self, text: str) -> str | None:
        if not self.pdf_service.split_range_valid(text):
            return None
        return text

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        if not isinstance(file_data, TextInputData):
            raise TypeError(f"Invalid file data: {type(file_data)}")

        async with self.pdf_service.split_pdf(file_data.id, file_data.text) as path:
            yield path
