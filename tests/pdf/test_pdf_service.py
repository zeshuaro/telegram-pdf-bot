from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from img2pdf import Rotation
from ocrmypdf.exceptions import EncryptedPdfError, PriorOcrFoundError, TaggedPDFError
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import PdfReadError as PyPdfReadError
from pypdf.pagerange import PageRange
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from pdf_bot.cli import CLIService, CLIServiceError
from pdf_bot.io_internal.io_service import IOService
from pdf_bot.models import FileData
from pdf_bot.pdf import (
    CompressResult,
    FontData,
    PdfDecryptError,
    PdfReadError,
    PdfService,
    ScaleByData,
    ScaleToData,
)
from pdf_bot.pdf.exceptions import (
    PdfEncryptedError,
    PdfIncorrectPasswordError,
    PdfNoImagesError,
    PdfNoTextError,
    PdfServiceError,
)
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestPDFService(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    PASSWORD = "password"

    def setup_method(self) -> None:
        super().setup_method()
        self.cli_service = MagicMock(spec=CLIService)
        self.telegram_service = self.mock_telegram_service()

        self.io_service = MagicMock(spec=IOService)
        self.io_service.create_temp_directory.return_value.__enter__.return_value = self.dir_path
        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = self.file_path
        self.io_service.create_temp_png_file.return_value.__enter__.return_value = self.file_path
        self.io_service.create_temp_txt_file.return_value.__enter__.return_value = self.file_path

        self.sut = PdfService(
            self.cli_service,
            self.io_service,
            self.telegram_service,
        )

        self.os_patcher = patch("pdf_bot.pdf.pdf_service.os")
        self.ocrmypdf_patcher = patch("pdf_bot.pdf.pdf_service.ocrmypdf")
        self.extract_text_patcher = patch("pdf_bot.pdf.pdf_service.extract_text")
        self.textwrap_patcher = patch("pdf_bot.pdf.pdf_service.textwrap")
        self.pdf_reader_patcher = patch("pdf_bot.pdf.pdf_service.PdfReader")
        self.pdf_writer_patcher = patch("pdf_bot.pdf.pdf_service.PdfWriter")

        self.mock_os = self.os_patcher.start()
        self.ocrmypdf = self.ocrmypdf_patcher.start()
        self.extract_text = self.extract_text_patcher.start()
        self.textwrap_patcher.start()
        self.pdf_reader_cls = self.pdf_reader_patcher.start()
        self.pdf_writer_cls = self.pdf_writer_patcher.start()

    def teardown_method(self) -> None:
        self.os_patcher.stop()
        self.ocrmypdf_patcher.stop()
        self.extract_text_patcher.stop()
        self.textwrap_patcher.stop()
        self.pdf_reader_patcher.stop()
        self.pdf_writer_patcher.stop()
        super().teardown_method()

    @pytest.mark.asyncio
    async def test_add_watermark_to_pdf(self) -> None:
        src_file_id = "src_file_id"
        wmk_file_id = "wmk_file_id"

        src_reader = MagicMock(spec=PdfReader)
        wmk_reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        src_reader.is_encrypted = wmk_reader.is_encrypted = False

        src_pages = [MagicMock(spec=PageObject) for _ in range(2)]
        src_reader.pages = src_pages

        wmk_page = MagicMock(spec=PageObject)
        wmk_reader.pages = [wmk_page]

        def pdf_file_reader_side_effect(file_id: str, *_args: Any, **_kwargs: Any) -> PdfReader:
            if file_id == src_file_id:
                return src_reader
            return wmk_reader

        self.telegram_service.download_pdf_file.side_effect = (
            self._async_context_manager_side_effect_echo
        )
        self.pdf_reader_cls.side_effect = pdf_file_reader_side_effect
        self.pdf_writer_cls.return_value = writer

        async with self.sut.add_watermark_to_pdf(src_file_id, wmk_file_id):
            assert self.telegram_service.download_pdf_file.call_count == 2
            download_calls = [call(src_file_id), call(wmk_file_id)]
            self.telegram_service.download_pdf_file.assert_has_calls(download_calls)

            add_page_calls = []
            for src_page in src_pages:
                src_page.merge_page.assert_called_once_with(wmk_page)
                add_page_calls.append(call(src_page))

            writer.add_page.assert_has_calls(add_page_calls)
            writer.write.assert_called_once()
            self.io_service.create_temp_pdf_file.assert_called_once_with("File_with_watermark")

    @pytest.mark.asyncio
    async def test_add_watermark_to_pdf_read_error(self) -> None:
        self.pdf_reader_cls.side_effect = PyPdfReadError()
        with pytest.raises(PdfReadError):
            async with self.sut.add_watermark_to_pdf(self.TELEGRAM_FILE_ID, self.TELEGRAM_FILE_ID):
                pass

        calls = [call(self.TELEGRAM_FILE_ID) for _ in range(2)]
        self.telegram_service.download_pdf_file.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_grayscale_pdf(self) -> None:
        image_paths = "image_paths"
        image_bytes = "image_bytes"
        buffered_writer = self.mock_path_open(self.file_path)

        with (
            patch("pdf_bot.pdf.pdf_service.pdf2image") as pdf2image,
            patch("pdf_bot.pdf.pdf_service.img2pdf") as img2pdf,
        ):
            pdf2image.convert_from_path.return_value = image_paths
            img2pdf.convert.return_value = image_bytes

            async with self.sut.grayscale_pdf(self.TELEGRAM_FILE_ID) as actual:
                assert actual == self.file_path
                self._assert_telegram_and_io_services("Grayscale")
                self.io_service.create_temp_directory.assert_called_once()
                pdf2image.convert_from_path.assert_called_once_with(
                    self.download_path,
                    output_folder=self.dir_path,
                    fmt="png",
                    grayscale=True,
                    paths_only=True,
                )
                img2pdf.convert.assert_called_once_with(image_paths, rotation=Rotation.ifvalid)
                self.file_path.open.assert_called_once_with("wb")
                buffered_writer.write.assert_called_once_with(image_bytes)

    @pytest.mark.asyncio
    async def test_compare_pdfs(self) -> None:
        file_ids = ["a", "b"]
        with patch("pdf_bot.pdf.pdf_service.pdf_diff") as pdf_diff:
            async with self.sut.compare_pdfs(*file_ids) as actual:
                assert actual == self.file_path
                calls = [call(x) for x in file_ids]
                self.telegram_service.download_pdf_file.assert_has_calls(calls, any_order=True)
                pdf_diff.main.assert_called_once_with(
                    files=[self.download_path, self.download_path],
                    out_file=self.file_path,
                )

    @pytest.mark.asyncio
    async def test_compress_pdf(self) -> None:
        old_size = 20
        new_size = 10

        download_stat = self.mock_path_stat(self.download_path)
        download_stat.st_size = old_size

        file_stat = self.mock_path_stat(self.file_path)
        file_stat.st_size = new_size

        async with self.sut.compress_pdf(self.TELEGRAM_FILE_ID) as compress_result:
            assert compress_result == CompressResult(old_size, new_size, self.file_path)
            self.cli_service.compress_pdf.assert_called_once_with(
                self.download_path, self.file_path
            )
            self._assert_telegram_and_io_services("Compressed")

    @pytest.mark.asyncio
    async def test_convert_to_images(self) -> None:
        with patch("pdf_bot.pdf.pdf_service.pdf2image") as pdf2image:
            async with self.sut.convert_pdf_to_images(self.TELEGRAM_FILE_ID) as actual:
                assert actual == self.dir_path
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
                pdf2image.convert_from_path.assert_called_once_with(
                    self.download_path, output_folder=self.dir_path, fmt="png"
                )

    @pytest.mark.parametrize("has_font_data", [True, False])
    @pytest.mark.asyncio
    async def test_create_pdf_from_text(self, has_font_data: bool) -> None:
        font_data = stylesheets = None
        html = MagicMock(spec=HTML)
        css = MagicMock(spec=CSS)
        font_config = MagicMock(spec=FontConfiguration)

        if has_font_data:
            font_data = FontData("family", "url")
            stylesheets = [css]

        with (
            patch("pdf_bot.pdf.pdf_service.HTML") as html_cls,
            patch("pdf_bot.pdf.pdf_service.CSS") as css_cls,
            patch("pdf_bot.pdf.pdf_service.FontConfiguration") as font_config_cls,
        ):
            html_cls.return_value = html
            css_cls.return_value = css
            font_config_cls.return_value = font_config

            async with self.sut.create_pdf_from_text(self.TELEGRAM_TEXT, font_data) as actual:
                assert actual == self.file_path
                html.write_pdf.assert_called_once()
                self.io_service.create_temp_pdf_file.assert_called_once_with("Text")
                html.write_pdf.assert_called_once_with(
                    self.file_path, stylesheets=stylesheets, font_config=font_config
                )

                if font_data is not None:
                    css_cls.assert_called_once_with(
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
                else:
                    css_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_crop_pdf_by_percentage(self) -> None:
        percent = 0.1

        with patch("pdf_bot.pdf.pdf_service.crop") as crop:
            async with self.sut.crop_pdf_by_percentage(self.TELEGRAM_FILE_ID, percent) as actual:
                assert actual == self.file_path
                crop.assert_called_once_with(
                    ["-p", str(percent), "-o", str(self.file_path), str(self.download_path)]
                )
                self._assert_telegram_and_io_services("Cropped")

    @pytest.mark.asyncio
    async def test_crop_pdf_by_margin_size(self) -> None:
        margin_size = 10

        with patch("pdf_bot.pdf.pdf_service.crop") as crop:
            async with self.sut.crop_pdf_by_margin_size(
                self.TELEGRAM_FILE_ID, margin_size
            ) as actual:
                assert actual == self.file_path
                crop.assert_called_once_with(
                    ["-a", str(margin_size), "-o", str(self.file_path), str(self.download_path)]
                )
                self._assert_telegram_and_io_services("Cropped")

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    @pytest.mark.asyncio
    async def test_decrypt_pdf(self, num_pages: int) -> None:
        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        reader.is_encrypted = True

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        async with self.sut.decrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("Decrypted")
            reader.decrypt.assert_called_once_with(self.PASSWORD)

            calls = [call(page) for page in pages]
            writer.add_page.assert_has_calls(calls)

    @pytest.mark.asyncio
    async def test_decrypt_pdf_not_encrypted(self) -> None:
        reader = MagicMock(spec=PdfReader)
        reader.is_encrypted = False
        self.pdf_reader_cls.return_value = reader

        with pytest.raises(PdfDecryptError):
            async with self.sut.decrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD):
                pass

        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        reader.decrypt.assert_not_called()
        self.io_service.create_temp_pdf_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_decrypt_pdf_incorrect_password(self) -> None:
        reader = MagicMock(spec=PdfReader)
        reader.is_encrypted = True
        reader.decrypt.return_value = 0
        self.pdf_reader_cls.return_value = reader

        with pytest.raises(PdfIncorrectPasswordError):
            async with self.sut.decrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD):
                pass
        self._assert_decrypt_failure(reader)

    @pytest.mark.asyncio
    async def test_decrypt_pdf_invalid_encryption_method(self) -> None:
        reader = MagicMock(spec=PdfReader)
        reader.is_encrypted = True
        reader.decrypt.side_effect = NotImplementedError()
        self.pdf_reader_cls.return_value = reader

        with pytest.raises(PdfDecryptError):
            async with self.sut.decrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD):
                pass
        self._assert_decrypt_failure(reader)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    @pytest.mark.asyncio
    async def test_encrypt_pdf(self, num_pages: int) -> None:
        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        reader.is_encrypted = False

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        async with self.sut.encrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("Encrypted")
            writer.encrypt.assert_called_once_with(self.PASSWORD)

            calls = [call(page) for page in pages]
            writer.add_page.assert_has_calls(calls)

    @pytest.mark.asyncio
    async def test_encrypt_pdf_already_encrypted(self) -> None:
        reader = MagicMock(spec=PdfReader)
        reader.is_encrypted = True
        self.pdf_reader_cls.return_value = reader

        with pytest.raises(PdfEncryptedError):
            async with self.sut.encrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD):
                pass

        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        self.io_service.create_temp_pdf_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_pdf_text(self) -> None:
        async with self.sut.extract_pdf_text(self.TELEGRAM_FILE_ID) as actual:
            assert actual == self.file_path
            self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
            self.io_service.create_temp_txt_file.assert_called_once_with("PDF_text")
            self.extract_text.assert_called_once_with(self.download_path)

    @pytest.mark.asyncio
    async def test_extract_pdf_text_error(self) -> None:
        self.extract_text.side_effect = PDFPasswordIncorrect

        with pytest.raises(PdfEncryptedError):
            async with self.sut.extract_pdf_text(self.TELEGRAM_FILE_ID):
                pass

        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        self.io_service.create_temp_txt_file.assert_not_called()
        self.extract_text.assert_called_once_with(self.download_path)

    @pytest.mark.asyncio
    async def test_extract_pdf_text_no_text(self) -> None:
        self.extract_text.return_value = ""

        with pytest.raises(PdfNoTextError):
            async with self.sut.extract_pdf_text(self.TELEGRAM_FILE_ID):
                pass

        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        self.io_service.create_temp_txt_file.assert_not_called()
        self.extract_text.assert_called_once_with(self.download_path)

    @pytest.mark.asyncio
    async def test_extract_pdf_images(self) -> None:
        async with self.sut.extract_pdf_images(self.TELEGRAM_FILE_ID) as actual:
            assert actual == self.dir_path
            self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
            self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
            self.cli_service.extract_pdf_images.assert_called_once_with(
                self.download_path, self.dir_path
            )
            self.mock_os.listdir.assert_called_once_with(self.dir_path)

    @pytest.mark.asyncio
    async def test_extract_pdf_images_no_images(self) -> None:
        self.mock_os.listdir.return_value = []

        with pytest.raises(PdfNoImagesError):
            async with self.sut.extract_pdf_images(self.TELEGRAM_FILE_ID):
                pass

        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
        self.cli_service.extract_pdf_images.assert_called_once_with(
            self.download_path, self.dir_path
        )
        self.mock_os.listdir.assert_called_once_with(self.dir_path)

    @pytest.mark.asyncio
    async def test_extract_pdf_images_cli_error(self) -> None:
        self.cli_service.extract_pdf_images.side_effect = CLIServiceError()

        with pytest.raises(PdfServiceError):
            async with self.sut.extract_pdf_images(self.TELEGRAM_FILE_ID):
                pass

        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
        self.cli_service.extract_pdf_images.assert_called_once_with(
            self.download_path, self.dir_path
        )
        self.mock_os.listdir.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_files", [0, 1, 2, 5])
    async def test_merge_pdfs(self, num_files: int) -> None:
        file_data_list, file_ids, file_paths = self._get_file_data_list(num_files)
        writer = MagicMock(spec=PdfWriter)
        self.pdf_writer_cls.return_value = writer
        self.telegram_service.download_files.return_value.__aenter__.return_value = file_paths

        async with self.sut.merge_pdfs(file_data_list):
            self.telegram_service.download_files.assert_called_once_with(file_ids)
            calls = [call(x) for x in file_paths]
            writer.append.assert_has_calls(calls)
            self.io_service.create_temp_pdf_file.assert_called_once_with("Merged")
            writer.write.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("exception", [PyPdfReadError(), ValueError()])
    async def test_merge_pdfs_read_error(self, exception: Exception) -> None:
        file_data_list, file_ids, file_paths = self._get_file_data_list(2)
        writer = MagicMock(spec=PdfWriter)
        writer.append.side_effect = exception
        self.pdf_writer_cls.return_value = writer
        self.telegram_service.download_files.return_value.__aenter__.return_value = file_paths

        with pytest.raises(PdfReadError):
            async with self.sut.merge_pdfs(file_data_list):
                pass

        self.telegram_service.download_files.assert_called_once_with(file_ids)
        self.io_service.create_temp_pdf_file.assert_not_called()
        writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_ocr_pdf(self) -> None:
        async with self.sut.ocr_pdf(self.TELEGRAM_FILE_ID) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("OCR")
            self.ocrmypdf.ocr.assert_called_once_with(
                self.download_path, self.file_path, progress_bar=False
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (PriorOcrFoundError, PdfServiceError),
            (TaggedPDFError, PdfServiceError),
            (EncryptedPdfError, PdfEncryptedError),
        ],
    )
    async def test_ocr_pdf_error(self, error: type[Exception], expected: type[Exception]) -> None:
        self.ocrmypdf.ocr.side_effect = error

        with pytest.raises(expected):
            async with self.sut.ocr_pdf(self.TELEGRAM_FILE_ID):
                pass

        self._assert_telegram_and_io_services("OCR")
        self.ocrmypdf.ocr.assert_called_once_with(
            self.download_path, self.file_path, progress_bar=False
        )

    @pytest.mark.asyncio
    async def test_preview_pdf(self) -> None:
        pdf_path = "pdf_path"
        out_path = "out_path"

        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        page = MagicMock(spec=PageObject)
        reader.is_encrypted = False
        reader.pages = [page]

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        image = MagicMock()

        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = pdf_path
        self.io_service.create_temp_png_file.return_value.__enter__.return_value = out_path

        with patch("pdf_bot.pdf.pdf_service.pdf2image") as pdf2image:
            pdf2image.convert_from_path.return_value = [image]

            async with self.sut.preview_pdf(self.TELEGRAM_FILE_ID) as actual:
                assert actual == out_path
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                writer.add_page.assert_called_once_with(page)
                pdf2image.convert_from_path.assert_called_once_with(pdf_path, fmt="png")
                image.save.assert_called_once_with(out_path)

    @pytest.mark.asyncio
    async def test_rename_pdf(self) -> None:
        file_name = "file_name"
        with patch("pdf_bot.pdf.pdf_service.shutil") as shutil:
            expected = self.dir_path / file_name
            async with self.sut.rename_pdf(self.TELEGRAM_FILE_ID, file_name) as actual:
                assert actual == expected
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                self.io_service.create_temp_directory.assert_called_once()
                shutil.copy.assert_called_once_with(self.download_path, expected)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    @pytest.mark.asyncio
    async def test_rotate_pdf(self, num_pages: int) -> None:
        degree = 90
        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        reader.is_encrypted = False

        pages = [MagicMock(spec=PageObject) for _ in range(num_pages)]
        rotated_pages = [MagicMock() for _ in pages]
        for i, page in enumerate(pages):
            page.rotate.return_value = rotated_pages[i]
        reader.pages = pages

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        async with self.sut.rotate_pdf(self.TELEGRAM_FILE_ID, degree) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("Rotated")

            for page in pages:
                page.rotate.assert_called_once_with(degree)

            calls = [call(page) for page in rotated_pages]
            writer.add_page.assert_has_calls(calls)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    @pytest.mark.asyncio
    async def test_scale_pdf_by_factor(self, num_pages: int) -> None:
        scale_data = ScaleByData(1, 2)

        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        reader.is_encrypted = False

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        async with self.sut.scale_pdf_by_factor(self.TELEGRAM_FILE_ID, scale_data) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("Scaled")

            calls = []
            for page in pages:
                page.scale.assert_called_once_with(scale_data.x, scale_data.y)
                calls.append(call(page))
            writer.add_page.assert_has_calls(calls)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    @pytest.mark.asyncio
    async def test_scale_pdf_to_dimension(self, num_pages: int) -> None:
        scale_data = ScaleToData(1, 2)

        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        reader.is_encrypted = False

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        async with self.sut.scale_pdf_to_dimension(self.TELEGRAM_FILE_ID, scale_data) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("Scaled")

            calls = []
            for page in pages:
                page.scale_to.assert_called_once_with(scale_data.x, scale_data.y)
                calls.append(call(page))
            writer.add_page.assert_has_calls(calls)

    @pytest.mark.parametrize(
        "split_range",
        [
            ":",
            "7",
            "0:3",
            "7:",
            "-1",
            ":-1",
            "-2",
            "-2:",
            "-3:-1",
            "::2",
            "1:10:2",
            "::-1",
            "3:0:-1",
            "2:-1",
        ],
    )
    @pytest.mark.asyncio
    async def test_split_range_valid(self, split_range: str) -> None:
        assert self.sut.split_range_valid(split_range) is True

    @pytest.mark.asyncio
    async def test_split_range_invalid(self) -> None:
        assert self.sut.split_range_valid("clearly_invalid") is False

    @pytest.mark.asyncio
    async def test_split_pdf(self) -> None:
        split_range = "7:"
        reader = MagicMock(spec=PdfReader)
        writer = MagicMock(spec=PdfWriter)
        reader.is_encrypted = False

        self.pdf_reader_cls.return_value = reader
        self.pdf_writer_cls.return_value = writer

        async with self.sut.split_pdf(self.TELEGRAM_FILE_ID, split_range) as actual:
            assert actual == self.file_path
            self._assert_telegram_and_io_services("Split")
            writer.append.assert_called_once_with(reader, pages=PageRange(split_range))

    @staticmethod
    def _async_context_manager_side_effect_echo(
        return_value: str, *_args: Any, **_kwargs: Any
    ) -> MagicMock:
        mock = MagicMock()
        mock.__aenter__.return_value = return_value
        return mock

    @staticmethod
    def _method_side_effect_echo(return_value: str, *_args: Any, **_kwargs: Any) -> str:
        return return_value

    @staticmethod
    def _get_file_data_list(
        num_files: int,
    ) -> tuple[list[FileData], list[str], list[str]]:
        file_data_list = []
        file_ids = []
        file_paths = []

        for i in range(num_files):
            file_data = FileData(f"id_{i}", f"name_{i}")
            file_data_list.append(file_data)
            file_ids.append(file_data.id)
            file_paths.append(f"path_{i}")

        return file_data_list, file_ids, file_paths

    def _assert_telegram_and_io_services(self, temp_pdf_file_prefix: str) -> None:
        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        self.io_service.create_temp_pdf_file.assert_called_once_with(temp_pdf_file_prefix)

    def _assert_decrypt_failure(self, reader: MagicMock) -> None:
        self.telegram_service.download_pdf_file.assert_called_once_with(self.TELEGRAM_FILE_ID)
        reader.decrypt.assert_called_once_with(self.PASSWORD)
        self.io_service.create_temp_pdf_file.assert_not_called()
