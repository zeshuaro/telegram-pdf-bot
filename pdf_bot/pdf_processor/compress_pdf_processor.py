from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class CompressPdfData(FileData):
    pass


class CompressPdfProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.compress_pdf

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Compress"), CompressPdfData)

    @property
    def handler(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.process_file, pattern=CompressPdfData)

    @asynccontextmanager
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        async with self.pdf_service.compress_pdf(file_data.id) as result:
            yield FileTaskResult(
                result.out_path,
                _("File size reduced by {percent}, from {old_size} to {new_size}").format(
                    percent=f"{result.reduced_percentage:.0%}",
                    old_size=result.readable_old_size,
                    new_size=result.readable_new_size,
                ),
            )
