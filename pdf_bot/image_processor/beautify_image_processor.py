from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import BaseHandler, CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_image_processor import AbstractImageProcessor


class BeautifyImageData(FileData):
    pass


class BeautifyImageProcessor(AbstractImageProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.beautify_image

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Beautify"), BeautifyImageData)

    @property
    def handler(self) -> BaseHandler | None:
        return CallbackQueryHandler(self.process_file, pattern=BeautifyImageData)

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.image_service.beautify_and_convert_images_to_pdf(
            [file_data]
        ) as path:
            yield path
