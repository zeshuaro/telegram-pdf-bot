from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import BaseHandler, CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_image_processor import AbstractImageProcessor


class ImageToPdfData(FileData):
    pass


class ImageToPdfProcessor(AbstractImageProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.image_to_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("To PDF"), ImageToPdfData)

    @property
    def handler(self) -> BaseHandler | None:
        return CallbackQueryHandler(self.process_file, pattern=ImageToPdfData)

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.image_service.convert_images_to_pdf(
            [FileData(file_id)]
        ) as path:
            yield path
