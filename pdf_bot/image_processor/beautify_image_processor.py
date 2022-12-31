from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData

from .abstract_image_processor import AbstractImageProcessor


class BeautifyImageData(FileData):
    pass


class BeautifyImageProcessor(AbstractImageProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.beautify_image

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Beautify"), BeautifyImageData)

    @property
    def handler(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.process_file, pattern=BeautifyImageData)

    @asynccontextmanager
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        async with self.image_service.beautify_and_convert_images_to_pdf([file_data]) as path:
            yield FileTaskResult(path)
