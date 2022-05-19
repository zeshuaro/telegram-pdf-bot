import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Generator

import pdf_diff

from pdf_bot.telegram import TelegramService


class PdfService:
    def __init__(self, telegram_service: TelegramService) -> None:
        self.telegram_service = telegram_service

    @contextmanager
    def compare_pdfs(
        self, file_id_a: str, file_id_b: str
    ) -> Generator[str, None, None]:
        with self.telegram_service.download_file(
            file_id_a
        ) as file_name_a, self.telegram_service.download_file(file_id_b) as file_name_b:
            try:
                td = TemporaryDirectory()
                out_fn = os.path.join(td.name, "Differences.png")
                pdf_diff.main(files=[file_name_a, file_name_b], out_file=out_fn)
                yield out_fn
            finally:
                td.cleanup()
