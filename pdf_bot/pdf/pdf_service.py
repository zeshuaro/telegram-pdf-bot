import gettext
import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Generator

import pdf_diff
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError as PyPdfReadError

from pdf_bot.pdf.exceptions import PdfEncryptError, PdfReadError
from pdf_bot.telegram import TelegramService

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


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

    @contextmanager
    def add_watermark_to_pdf(self, source_file_id, watermark_file_id):
        src_reader = self.open_pdf(source_file_id)
        wmk_reader = self.open_pdf(watermark_file_id)
        wmk_page = wmk_reader.getPage(0)
        writer = PdfFileWriter()

        for page in src_reader.pages:
            page.mergePage(wmk_page)
            writer.addPage(page)

        try:
            td = TemporaryDirectory()
            out_fn = os.path.join(td.name, "File_watermark.pdf")
            with open(out_fn, "wb") as f:
                writer.write(f)
            yield out_fn
        finally:
            td.cleanup()

    def open_pdf(self, file_id: str, allow_encrypted: bool = False) -> PdfFileReader:
        with self.telegram_service.download_file(file_id) as file_name:
            try:
                pdf_reader = PdfFileReader(open(file_name, "rb"))
            except PyPdfReadError as e:
                raise PdfReadError(_("Your PDF file is invalid")) from e

            if pdf_reader.isEncrypted and not allow_encrypted:
                raise PdfEncryptError(_("Your PDF file is encrypted"))

            return pdf_reader
