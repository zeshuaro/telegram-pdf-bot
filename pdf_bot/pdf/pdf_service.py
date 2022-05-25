import gettext
from contextlib import contextmanager
from typing import Generator, List

import pdf_diff
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError as PyPdfReadError
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from pdf_bot.io import IOService
from pdf_bot.pdf.exceptions import PdfEncryptError, PdfReadError
from pdf_bot.telegram import TelegramService
from pdf_bot.text.models import FontData

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


class PdfService:
    def __init__(
        self, io_service: IOService, telegram_service: TelegramService
    ) -> None:
        self.io_service = io_service
        self.telegram_service = telegram_service

    @contextmanager
    def add_watermark_to_pdf(self, source_file_id, watermark_file_id):
        src_reader = self._open_pdf(source_file_id)
        wmk_reader = self._open_pdf(watermark_file_id)
        wmk_page = wmk_reader.getPage(0)
        writer = PdfFileWriter()

        for page in src_reader.pages:
            page.mergePage(wmk_page)
            writer.addPage(page)

        with self.io_service.create_temp_pdf_file(
            prefix="File_with_watermark"
        ) as out_path:
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
                yield out_path
            finally:
                pass

    @contextmanager
    def create_pdf_from_text(self, text: str, font_data: FontData | None):
        html = HTML(
            string="<p>{content}</p>".format(content=text.replace("\n", "<br/>"))
        )
        font_config = FontConfiguration()
        stylesheets: List[CSS] = None

        if font_data is not None:
            stylesheets = [
                CSS(
                    string=(
                        "@font-face {"
                        f"font-family: {font_data.font_family};"
                        f"src: url({font_data.font_url});"
                        "}"
                        "p {"
                        f"font-family: {font_data.font_family};"
                        "}"
                    ),
                    font_config=font_config,
                )
            ]

        try:
            with self.io_service.create_temp_pdf_file(prefix="Text") as out_path:
                html.write_pdf(
                    out_path, stylesheets=stylesheets, font_config=font_config
                )
                yield out_path
        finally:
            pass

    @contextmanager
    def compare_pdfs(
        self, file_id_a: str, file_id_b: str
    ) -> Generator[str, None, None]:
        with self.telegram_service.download_file(
            file_id_a
        ) as file_name_a, self.telegram_service.download_file(
            file_id_b
        ) as file_name_b, self.io_service.create_temp_png_file(
            prefix="Differences"
        ) as out_path:
            try:
                pdf_diff.main(files=[file_name_a, file_name_b], out_file=out_path)
                yield out_path
            finally:
                pass

    def _open_pdf(self, file_id: str, allow_encrypted: bool = False) -> PdfFileReader:
        with self.telegram_service.download_file(file_id) as file_name:
            try:
                pdf_reader = PdfFileReader(open(file_name, "rb"))
            except PyPdfReadError as e:
                raise PdfReadError(_("Your PDF file is invalid")) from e

            if pdf_reader.isEncrypted and not allow_encrypted:
                raise PdfEncryptError(_("Your PDF file is encrypted"))

            return pdf_reader
