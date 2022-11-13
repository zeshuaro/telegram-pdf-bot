import gettext
from contextlib import contextmanager
from typing import Generator

from pdf_bot.analytics import TaskType
from pdf_bot.crypto.abstract_crypto_service import AbstractCryptoService

_ = gettext.gettext


class EncryptService(AbstractCryptoService):
    def get_wait_password_state(self) -> str:
        return "wait_encrypt_password"

    def get_wait_password_text(self) -> str:
        return _("Send me the password to encrypt your PDF file")

    def get_task_type(self) -> TaskType:
        return TaskType.encrypt_pdf

    @contextmanager
    def process_pdf_task(
        self, file_id: str, password: str
    ) -> Generator[str, None, None]:
        with self.pdf_service.encrypt_pdf(file_id, password) as path:
            yield path
