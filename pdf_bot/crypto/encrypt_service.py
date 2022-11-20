from contextlib import contextmanager
from gettext import gettext as _
from typing import Generator

from pdf_bot.analytics import TaskType
from pdf_bot.crypto.abstract_crypto_service import AbstractCryptoService


class EncryptService(AbstractCryptoService):
    @property
    def wait_password_state(self) -> str:
        return "wait_encrypt_password"

    @property
    def wait_password_text(self) -> str:
        return _("Send me the password to encrypt your PDF file")

    @property
    def task_type(self) -> TaskType:
        return TaskType.encrypt_pdf

    @contextmanager
    def process_file_task(
        self, file_id: str, message_text: str
    ) -> Generator[str, None, None]:
        with self.pdf_service.encrypt_pdf(file_id, message_text) as path:
            yield path
