import asyncio
import os
import shutil
import textwrap
from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

import img2pdf
import ocrmypdf
import pdf2image
import pdf_diff
from img2pdf import Rotation
from ocrmypdf.exceptions import EncryptedPdfError, PriorOcrFoundError
from pdfCropMargins import crop
from pdfminer.high_level import extract_text
from pdfminer.pdfdocument import PDFPasswordIncorrect
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from PyPDF2.errors import PdfReadError as PyPdfReadError
from PyPDF2.pagerange import PageRange
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from pdf_bot.cli import CLIService, CLIServiceError
from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.pdf.exceptions import (
    PdfDecryptError,
    PdfEncryptedError,
    PdfIncorrectPasswordError,
    PdfNoImagesError,
    PdfNoTextError,
    PdfReadError,
    PdfServiceError,
)
from pdf_bot.pdf.models import CompressResult, FontData, ScaleData
from pdf_bot.telegram_internal import TelegramService


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

    @asynccontextmanager
    async def add_watermark_to_pdf(
        self, source_file_id: str, watermark_file_id: str
    ) -> AsyncGenerator[str, None]:
        src_reader, wmk_reader = await asyncio.gather(
            self._open_pdf(source_file_id), self._open_pdf(watermark_file_id)
        )
        wmk_page = wmk_reader.pages[0]
        writer = PdfFileWriter()

        for page in src_reader.pages:
            page.merge_page(wmk_page)
            writer.add_page(page)

        with self.io_service.create_temp_pdf_file("File_with_watermark") as out_path:
            with open(out_path, "wb") as f:
                writer.write(f)
            yield out_path

    @asynccontextmanager
    async def grayscale_pdf(self, file_id: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with (
                self.io_service.create_temp_directory() as dir_name,
                self.io_service.create_temp_pdf_file("Grayscale") as out_path,
            ):
                images = pdf2image.convert_from_path(
                    file_path,
                    output_folder=dir_name,
                    fmt="png",
                    grayscale=True,
                    paths_only=True,
                )

                with open(out_path, "wb") as f:
                    f.write(img2pdf.convert(images, rotation=Rotation.ifvalid))
                yield out_path

    @asynccontextmanager
    async def compare_pdfs(self, file_id_a: str, file_id_b: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(
            file_id_a
        ) as file_name_a, self.telegram_service.download_pdf_file(file_id_b) as file_name_b:
            with self.io_service.create_temp_png_file("Differences") as out_path:
                pdf_diff.main(files=[file_name_a, file_name_b], out_file=out_path)
                yield out_path

    @asynccontextmanager
    async def compress_pdf(self, file_id: str) -> AsyncGenerator[CompressResult, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_pdf_file("Compressed") as out_path:
                self.cli_service.compress_pdf(file_path, out_path)
                old_size = os.path.getsize(file_path)
                new_size = os.path.getsize(out_path)
                yield CompressResult(old_size, new_size, out_path)

    @asynccontextmanager
    async def convert_pdf_to_images(self, file_id: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_directory("PDF_images") as out_dir:
                pdf2image.convert_from_path(file_path, output_folder=out_dir, fmt="png")
                yield out_dir

    @asynccontextmanager
    async def create_pdf_from_text(
        self, text: str, font_data: FontData | None
    ) -> AsyncGenerator[str, None]:
        html = HTML(string="<p>{content}</p>".format(content=text.replace("\n", "<br/>")))
        font_config = FontConfiguration()
        stylesheets: list[CSS] | None = None

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

        with self.io_service.create_temp_pdf_file("Text") as out_path:
            html.write_pdf(out_path, stylesheets=stylesheets, font_config=font_config)
            yield out_path

    @asynccontextmanager
    async def crop_pdf_by_percentage(
        self, file_id: str, percentage: float
    ) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_pdf_file("Cropped") as out_path:
                crop(["-p", str(percentage), "-o", out_path, file_path])
                yield out_path

    @asynccontextmanager
    async def crop_pdf_by_margin_size(
        self, file_id: str, margin_size: float
    ) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_pdf_file("Cropped") as out_path:
                crop(["-a", str(margin_size), "-o", out_path, file_path])
                yield out_path

    @asynccontextmanager
    async def decrypt_pdf(self, file_id: str, password: str) -> AsyncGenerator[str, None]:
        reader = await self._open_pdf(file_id, allow_encrypted=True)
        if not reader.is_encrypted:
            raise PdfDecryptError(_("Your PDF file is not encrypted"))

        try:
            if reader.decrypt(password) == 0:
                raise PdfIncorrectPasswordError(_("Incorrect password, please try again"))
        except NotImplementedError as e:
            raise PdfDecryptError(
                _("Your PDF file is encrypted with a method that I can't decrypt")
            ) from e

        writer = PdfFileWriter()
        for page in reader.pages:
            writer.add_page(page)

        with self.io_service.create_temp_pdf_file("Decrypted") as out_path:
            with open(out_path, "wb") as f:
                writer.write(f)
            yield out_path

    @asynccontextmanager
    async def encrypt_pdf(self, file_id: str, password: str) -> AsyncGenerator[str, None]:
        reader = await self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        with self.io_service.create_temp_pdf_file("Encrypted") as out_path:
            with open(out_path, "wb") as f:
                writer.write(f)
            yield out_path

    @asynccontextmanager
    async def extract_pdf_images(self, file_id: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_directory("PDF_images") as out_dir:
                try:
                    self.cli_service.extract_pdf_images(file_path, out_dir)
                except CLIServiceError as e:
                    raise PdfServiceError(e) from e

                if not os.listdir(out_dir):
                    raise PdfNoImagesError(_("No images found in your PDF file"))
                yield out_dir

    @asynccontextmanager
    async def extract_pdf_text(self, file_id: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            try:
                text = extract_text(file_path)
            except PDFPasswordIncorrect as e:
                raise PdfEncryptedError() from e

        if not text:
            raise PdfNoTextError(_("No text found in your PDF file"))

        wrapped_text = textwrap.wrap(text)
        with self.io_service.create_temp_txt_file("PDF_text") as out_path:
            with open(out_path, "w") as f:
                f.write("\n".join(wrapped_text))
            yield out_path

    @asynccontextmanager
    async def merge_pdfs(self, file_data_list: list[FileData]) -> AsyncGenerator[str, None]:
        file_ids = self._get_file_ids(file_data_list)
        merger = PdfFileMerger()

        async with self.telegram_service.download_files(file_ids) as file_paths:
            for i, file_path in enumerate(file_paths):
                try:
                    merger.append(file_path)
                except (PyPdfReadError, ValueError) as e:
                    raise PdfReadError(
                        _(
                            "I couldn't merge your PDF files as this file is invalid: "
                            "{file_name}".format(file_name=file_data_list[i].name)
                        )
                    ) from e

        with self.io_service.create_temp_pdf_file("Merged_files") as out_path:
            with open(out_path, "wb") as f:
                merger.write(f)
            yield out_path

    @asynccontextmanager
    async def ocr_pdf(self, file_id: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_pdf_file("OCR") as out_path:
                try:
                    ocrmypdf.ocr(file_path, out_path, progress_bar=False)
                    yield out_path
                except PriorOcrFoundError as e:
                    raise PdfServiceError(_("Your PDF file already has a text layer")) from e
                except EncryptedPdfError as e:
                    raise PdfEncryptedError() from e

    @asynccontextmanager
    async def preview_pdf(self, file_id: str) -> AsyncGenerator[str, None]:
        with (
            self.io_service.create_temp_pdf_file() as pdf_path,
            self.io_service.create_temp_png_file("Preview") as out_path,
        ):
            reader = await self._open_pdf(file_id)
            writer = PdfFileWriter()
            writer.add_page(reader.pages[0])

            # Write cover preview PDF file
            with open(pdf_path, "wb") as f:
                writer.write(f)

            # Convert cover preview to image
            imgs = pdf2image.convert_from_path(pdf_path, fmt="png")
            imgs[0].save(out_path)
            yield out_path

    @asynccontextmanager
    async def rename_pdf(self, file_id: str, file_name: str) -> AsyncGenerator[str, None]:
        async with self.telegram_service.download_pdf_file(file_id) as file_path:
            with self.io_service.create_temp_directory() as dir_name:
                out_path = os.path.join(dir_name, file_name)
                shutil.copy(file_path, out_path)
                yield out_path

    @asynccontextmanager
    async def rotate_pdf(self, file_id: str, degree: int) -> AsyncGenerator[str, None]:
        reader = await self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            writer.add_page(page.rotate_clockwise(degree))

        with self.io_service.create_temp_pdf_file("Rotated") as out_path:
            with open(out_path, "wb") as f:
                writer.write(f)
            yield out_path

    @asynccontextmanager
    async def scale_pdf_by_factor(
        self, file_id: str, scale_data: ScaleData
    ) -> AsyncGenerator[str, None]:
        reader = await self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            page.scale(scale_data.x, scale_data.y)
            writer.add_page(page)

        with self.io_service.create_temp_pdf_file("Scaled") as out_path:
            with open(out_path, "wb") as f:
                writer.write(f)
            yield out_path

    @asynccontextmanager
    async def scale_pdf_to_dimension(
        self, file_id: str, scale_data: ScaleData
    ) -> AsyncGenerator[str, None]:
        reader = await self._open_pdf(file_id)
        writer = PdfFileWriter()

        for page in reader.pages:
            page.scale_to(scale_data.x, scale_data.y)
            writer.add_page(page)

        with self.io_service.create_temp_pdf_file("Scaled") as out_path:
            with open(out_path, "wb") as f:
                writer.write(f)
            yield out_path

    @staticmethod
    def split_range_valid(split_range: str) -> bool:
        return PageRange.valid(split_range)

    @asynccontextmanager
    async def split_pdf(self, file_id: str, split_range: str) -> AsyncGenerator[str, None]:
        reader = await self._open_pdf(file_id)
        merger = PdfFileMerger()
        merger.append(reader, pages=PageRange(split_range))

        with self.io_service.create_temp_pdf_file("Split") as out_path:
            with open(out_path, "wb") as f:
                merger.write(f)
            yield out_path

    @staticmethod
    def _get_file_ids(file_data_list: list[FileData]) -> list[str]:
        return [x.id for x in file_data_list]

    async def _open_pdf(self, file_id: str, allow_encrypted: bool = False) -> PdfFileReader:
        async with self.telegram_service.download_pdf_file(file_id) as file_name:
            try:
                pdf_reader = PdfFileReader(file_name)
            except PyPdfReadError as e:
                raise PdfReadError(_("Your PDF file is invalid")) from e

        if pdf_reader.is_encrypted and not allow_encrypted:
            raise PdfEncryptedError()
        return pdf_reader
