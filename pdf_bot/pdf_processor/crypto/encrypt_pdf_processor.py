from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData

from .abstract_crypto_pdf_processor import AbstractCryptoPdfProcessor


class EncryptPdfProcessor(AbstractCryptoPdfProcessor):
    @property
    def wait_password_state(self) -> str:
        return "wait_encrypt_password"

    @property
    def wait_password_text(self) -> str:
        return _("Send me the password to encrypt your PDF file")

    @property
    def task_type(self) -> TaskType:
        return TaskType.encrypt_pdf

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.encrypt_pdf(file_data.id, message_text) as path:
            yield path
