import gettext
import os
import shutil
from contextlib import contextmanager
from typing import Generator, List

import img2pdf
import noteshrink
import ocrmypdf
import pdf2image
import pdf_diff
from ocrmypdf.exceptions import PriorOcrFoundError
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from PyPDF2.errors import PdfReadError as PyPdfReadError
from PyPDF2.pagerange import PageRange
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from pdf_bot.cli import CLIService
from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.pdf.exceptions import (
    PdfDecryptError,
    PdfEncryptError,
    PdfIncorrectPasswordError,
    PdfOcrError,
    PdfReadError,
)
from pdf_bot.pdf.models import CompressResult, FontData, ScaleByData, ScaleData
from pdf_bot.telegram import TelegramService

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


class PdfService:
    def __init__(
        self,
        cli_service: CLIService,
        io_service: IOService,
        telegram_service: TelegramService,
    ) -> None:
        self.cli_service = cli_service
        self.io_service = io_service
        self.telegram_service = telegram_service

    @contextmanager
    def add_watermark_to_pdf(self, source_file_id, watermark_file_id):
        src_reader = self._open_pdf(source_file_id)
        wmk_reader = self._open_pdf(watermark_file_id)
        wmk_page = wmk_reader.pages[0]
        writer = PdfFileWriter()

        for page in src_reader.pages:
            page.merge_page(wmk_page)
            writer.add_page(page)

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
    def beautify_and_convert_images_to_pdf(self, file_data_list: List[FileData]):
        file_ids = self._get_file_ids(file_data_list)
        with self.telegram_service.download_files(
            file_ids
        ) as file_paths, self.io_service.create_temp_pdf_file(
            prefix="Beautified"
        ) as out_path:
            try:
                out_path_base = os.path.splitext(out_path)[0]
                noteshrink.notescan_main(
                    file_paths, basename=f"{out_path_base}_page", pdfname=out_path
                )
                yield out_path
            finally:
                pass

    @contextmanager
    def black_and_white_pdf(self, file_id: str):
        with (
            self.telegram_service.download_file(file_id) as file_path,
            self.io_service.create_temp_directory() as dir_name,
            self.io_service.create_temp_pdf_file(prefix="Black_and_White") as out_path,
        ):
            try:
                images = pdf2image.convert_from_path(
                    file_path,
                    output_folder=dir_name,
                    fmt="png",
                    grayscale=True,
                    paths_only=True,
                )

                with open(out_path, "wb") as f:
                    f.write(img2pdf.convert(images))
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

    @contextmanager
    def compress_pdf(self, file_id: str):
        with self.telegram_service.download_file(
            file_id
        ) as file_path, self.io_service.create_temp_pdf_file(
            prefix="Compressed"
        ) as out_path:
            try:
                self.cli_service.compress_pdf(file_path, out_path)
                old_size = os.path.getsize(file_path)
                new_size = os.path.getsize(out_path)
                yield CompressResult(old_size, new_size, out_path)
            finally:
                pass

    @contextmanager
    def convert_images_to_pdf(self, file_data_list: List[FileData]):
        file_ids = self._get_file_ids(file_data_list)
        with self.telegram_service.download_files(
            file_ids
        ) as file_paths, self.io_service.create_temp_pdf_file(
            prefix="Converted"
        ) as out_path:
            try:
                with open(out_path, "wb") as f:
                    f.write(img2pdf.convert(file_paths))
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
    def crop_pdf(
        self,
        file_id: str,
        percentage: float | None = None,
        margin_size: float | None = None,
    ):
        with self.telegram_service.download_file(
            file_id
        ) as file_path, self.io_service.create_temp_pdf_file(
            prefix="Cropped"
        ) as out_path:
            try:
                if percentage is not None:
                    self.cli_service.crop_pdf_by_percentage(
                        file_path, out_path, percentage
                    )
                else:
                    self.cli_service.crop_pdf_by_margin_size(
                        file_path, out_path, margin_size
                    )
                yield out_path
            finally:
                pass

    @contextmanager
    def decrypt_pdf(self, file_id: str, password: str):
        reader = self._open_pdf(file_id, allow_encrypted=True)
        if not reader.is_encrypted:
            raise PdfDecryptError(_("Your PDF file is not encrypted"))

        try:
            if reader.decrypt(password) == 0:
                raise PdfIncorrectPasswordError(
                    _("Incorrect password, please try again")
                )
        except NotImplementedError as e:
            raise PdfDecryptError(
                _("Your PDF file is encrypted with a method that I can't decrypt")
            ) from e

        writer = PdfFileWriter()
        for page in reader.pages:
            writer.add_page(page)

        with self.io_service.create_temp_pdf_file("Decrypted") as out_path:
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
                yield out_path
            finally:
                pass

    @contextmanager
    def encrypt_pdf(self, file_id: str, password: str):
        reader = self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        with self.io_service.create_temp_pdf_file("Encrypted") as out_path:
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
                yield out_path
            finally:
                pass

    @contextmanager
    def merge_pdfs(self, file_data_list: List[FileData]) -> Generator[str, None, None]:
        file_ids = self._get_file_ids(file_data_list)
        merger = PdfFileMerger()

        with self.telegram_service.download_files(file_ids) as file_paths:
            for i, file_path in enumerate(file_paths):
                try:
                    merger.append(open(file_path, "rb"))
                except (PyPdfReadError, ValueError) as e:
                    raise PdfReadError(
                        _(
                            "I couldn't merge your PDF files as this file is invalid: "
                            "{file_name}".format(file_name=file_data_list[i].name)
                        )
                    ) from e

        with self.io_service.create_temp_pdf_file(prefix="Merged_files") as out_path:
            try:
                with open(out_path, "wb") as f:
                    merger.write(f)
                yield out_path
            finally:
                pass

    @contextmanager
    def ocr_pdf(self, file_id: str) -> Generator[str, None, None]:
        with self.telegram_service.download_file(
            file_id
        ) as file_path, self.io_service.create_temp_pdf_file("OCR") as out_path:
            try:
                ocrmypdf.ocr(file_path, out_path, progress_bar=False)
                yield out_path
            except PriorOcrFoundError as e:
                raise PdfOcrError(_("Your PDF file already has a text layer")) from e
            finally:
                pass

    @contextmanager
    def rename_pdf(self, file_id: str, file_name: str) -> Generator[str, None, None]:
        with self.telegram_service.download_file(
            file_id
        ) as file_path, self.io_service.create_temp_directory() as dir_name:
            try:
                out_path = os.path.join(dir_name, file_name)
                shutil.copy(file_path, out_path)
                yield out_path
            finally:
                pass

    @contextmanager
    def rotate_pdf(self, file_id: str, degree: int):
        reader = self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            writer.add_page(page.rotate_clockwise(degree))

        with self.io_service.create_temp_pdf_file("Rotated") as out_path:
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
                yield out_path
            finally:
                pass

    @contextmanager
    def scale_pdf(self, file_id: str, scale_data: ScaleData):
        reader = self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            if isinstance(scale_data, ScaleByData):
                page.scale(scale_data.x, scale_data.y)
            else:
                page.scale_to(scale_data.x, scale_data.y)
            writer.add_page(page)

        with self.io_service.create_temp_pdf_file("Scaled") as out_path:
            try:
                with open(out_path, "wb") as f:
                    writer.write(f)
                yield out_path
            finally:
                pass

    @staticmethod
    def split_range_valid(split_range: str) -> bool:
        return PageRange.valid(split_range)

    @contextmanager
    def split_pdf(self, file_id: str, split_range: str):
        reader = self._open_pdf(file_id)
        merger = PdfFileMerger()
        merger.append(reader, pages=PageRange(split_range))

        with self.io_service.create_temp_pdf_file("Split") as out_path:
            try:
                with open(out_path, "wb") as f:
                    merger.write(f)
                yield out_path
            finally:
                pass

    @staticmethod
    def _get_file_ids(file_data_list: List[FileData]) -> List[str]:
        return [x.id for x in file_data_list]

    def _open_pdf(self, file_id: str, allow_encrypted: bool = False) -> PdfFileReader:
        with self.telegram_service.download_file(file_id) as file_name:
            try:
                pdf_reader = PdfFileReader(open(file_name, "rb"))
            except PyPdfReadError as e:
                raise PdfReadError(_("Your PDF file is invalid")) from e

        if pdf_reader.is_encrypted and not allow_encrypted:
            raise PdfEncryptError(_("Your PDF file is encrypted"))
        return pdf_reader
