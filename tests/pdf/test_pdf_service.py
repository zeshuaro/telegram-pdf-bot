from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from ocrmypdf.exceptions import PriorOcrFoundError
from PyPDF2 import PageObject, PdfFileMerger, PdfFileReader, PdfFileWriter
from PyPDF2.errors import PdfReadError as PyPdfReadError
from PyPDF2.pagerange import PageRange
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from pdf_bot.cli import CLIService, CLIServiceError
from pdf_bot.io.io_service import IOService
from pdf_bot.models import FileData
from pdf_bot.pdf import (
    CompressResult,
    FontData,
    PdfDecryptError,
    PdfOcrError,
    PdfReadError,
    PdfService,
    ScaleByData,
    ScaleToData,
)
from pdf_bot.pdf.exceptions import (
    PdfEncryptError,
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
    DOWNLOAD_PATH = "download_path"
    DIR_NAME = "dir_name"
    OUTPUT_PATH = "output_path"
    PASSWORD = "password"

    def setup_method(self) -> None:
        super().setup_method()
        self.cli_service = MagicMock(spec=CLIService)

        self.io_service = MagicMock(spec=IOService)
        self.io_service.create_temp_directory.return_value.__enter__.return_value = (
            self.DIR_NAME
        )
        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = (
            self.OUTPUT_PATH
        )
        self.io_service.create_temp_png_file.return_value.__enter__.return_value = (
            self.OUTPUT_PATH
        )
        self.io_service.create_temp_txt_file.return_value.__enter__.return_value = (
            self.OUTPUT_PATH
        )

        self.telegram_service = self.mock_telegram_service()
        self.telegram_service.download_pdf_file.return_value.__enter__.return_value = (
            self.DOWNLOAD_PATH
        )

        self.open_patcher = patch("builtins.open")
        self.mock_open = self.open_patcher.start()

        self.os_patcher = patch("pdf_bot.pdf.pdf_service.os")
        self.mock_os = self.os_patcher.start()

        self.sut = PdfService(
            self.cli_service,
            self.io_service,
            self.telegram_service,
        )

    def teardown_method(self) -> None:
        self.open_patcher.stop()
        self.os_patcher.stop()
        super().teardown_method()

    def test_add_watermark_to_pdf(self) -> None:
        src_file_id = "src_file_id"
        wmk_file_id = "wmk_file_id"

        src_reader = MagicMock(spec=PdfFileReader)
        wmk_reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        src_reader.is_encrypted = wmk_reader.is_encrypted = False

        src_pages = [MagicMock(spec=PageObject) for _ in range(2)]
        src_reader.pages = src_pages

        wmk_page = MagicMock(spec=PageObject)
        wmk_reader.pages = [wmk_page]

        def pdf_file_reader_side_effect(
            file_id: str, *_args: Any, **_kwargs: Any
        ) -> PdfFileReader:
            if file_id == src_file_id:
                return src_reader
            return wmk_reader

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls:
            self.telegram_service.download_pdf_file.side_effect = (
                self._context_manager_side_effect_echo
            )
            reader_cls.side_effect = pdf_file_reader_side_effect
            writer_cls.return_value = writer

            with self.sut.add_watermark_to_pdf(src_file_id, wmk_file_id):
                assert self.telegram_service.download_pdf_file.call_count == 2
                download_calls = [call(src_file_id), call(wmk_file_id)]
                self.telegram_service.download_pdf_file.assert_has_calls(download_calls)

                add_page_calls = []
                for src_page in src_pages:
                    src_page.merge_page.assert_called_once_with(wmk_page)
                    add_page_calls.append(call(src_page))

                writer.add_page.assert_has_calls(add_page_calls)
                writer.write.assert_called_once()
                self.io_service.create_temp_pdf_file.assert_called_once_with(
                    "File_with_watermark"
                )

    def test_add_watermark_to_pdf_read_error(self) -> None:
        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls:
            reader_cls.side_effect = PyPdfReadError()
            with pytest.raises(PdfReadError), self.sut.add_watermark_to_pdf(
                self.TELEGRAM_FILE_ID, self.TELEGRAM_FILE_ID
            ):
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )

    def test_black_and_white_pdf(self) -> None:
        image_paths = "image_paths"
        file = MagicMock()
        image_bytes = "image_bytes"

        with patch("pdf_bot.pdf.pdf_service.pdf2image") as pdf2image, patch(
            "pdf_bot.pdf.pdf_service.img2pdf"
        ) as img2pdf:
            self.mock_open.return_value.__enter__.return_value = file
            pdf2image.convert_from_path.return_value = image_paths
            img2pdf.convert.return_value = image_bytes

            with self.sut.black_and_white_pdf(self.TELEGRAM_FILE_ID) as actual:
                assert actual == self.OUTPUT_PATH
                self._assert_telegram_and_io_services("Black_and_white")
                self.io_service.create_temp_directory.assert_called_once()
                pdf2image.convert_from_path.assert_called_once_with(
                    self.DOWNLOAD_PATH,
                    output_folder=self.DIR_NAME,
                    fmt="png",
                    grayscale=True,
                    paths_only=True,
                )
                img2pdf.convert.assert_called_once_with(image_paths)
                self.mock_open.assert_called_once_with(self.OUTPUT_PATH, "wb")
                file.write.assert_called_once_with(image_bytes)

    def test_compare_pdfs(self) -> None:
        file_ids = ["a", "b"]
        with patch(
            "pdf_bot.pdf.pdf_service.pdf_diff"
        ) as pdf_diff, self.sut.compare_pdfs(*file_ids) as actual:
            assert actual == self.OUTPUT_PATH
            calls = [call(x) for x in file_ids]
            self.telegram_service.download_pdf_file.assert_has_calls(
                calls, any_order=True
            )
            pdf_diff.main.assert_called_once_with(
                files=[self.DOWNLOAD_PATH, self.DOWNLOAD_PATH],
                out_file=self.OUTPUT_PATH,
            )

    def test_compress_pdf(self) -> None:
        old_size = 20
        new_size = 10

        def getsize_side_effect(path: str, *_args: Any, **_kwargs: Any) -> int:
            if path == self.DOWNLOAD_PATH:
                return old_size
            return new_size

        with patch("pdf_bot.pdf.pdf_service.os") as mock_os:
            mock_os.path.getsize.side_effect = getsize_side_effect
            with self.sut.compress_pdf(self.TELEGRAM_FILE_ID) as compress_result:
                assert compress_result == CompressResult(
                    old_size, new_size, self.OUTPUT_PATH
                )
                self.cli_service.compress_pdf.assert_called_once_with(
                    self.DOWNLOAD_PATH, self.OUTPUT_PATH
                )
                self._assert_telegram_and_io_services("Compressed")

    def test_convert_to_images(self) -> None:
        with patch(
            "pdf_bot.pdf.pdf_service.pdf2image"
        ) as pdf2image, self.sut.convert_pdf_to_images(self.TELEGRAM_FILE_ID) as actual:
            assert actual == self.DIR_NAME
            self.telegram_service.download_pdf_file.assert_called_once_with(
                self.TELEGRAM_FILE_ID
            )
            self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
            pdf2image.convert_from_path.assert_called_once_with(
                self.DOWNLOAD_PATH, output_folder=self.DIR_NAME, fmt="png"
            )

    @pytest.mark.parametrize("has_font_data", [True, False])
    def test_create_pdf_from_text(self, has_font_data: bool) -> None:
        font_data = stylesheets = None
        html = MagicMock(spec=HTML)
        css = MagicMock(spec=CSS)
        font_config = MagicMock(spec=FontConfiguration)

        if has_font_data:
            font_data = FontData("family", "url")
            stylesheets = [css]

        with patch("pdf_bot.pdf.pdf_service.HTML") as html_cls, patch(
            "pdf_bot.pdf.pdf_service.CSS"
        ) as css_cls, patch(
            "pdf_bot.pdf.pdf_service.FontConfiguration"
        ) as font_config_cls:
            html_cls.return_value = html
            css_cls.return_value = css
            font_config_cls.return_value = font_config

            with self.sut.create_pdf_from_text(self.TELEGRAM_TEXT, font_data) as actual:
                assert actual == self.OUTPUT_PATH
                html.write_pdf.assert_called_once()
                self.io_service.create_temp_pdf_file.assert_called_once_with("Text")
                html.write_pdf.assert_called_once_with(
                    self.OUTPUT_PATH, stylesheets=stylesheets, font_config=font_config
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

    def test_crop_pdf_by_percentage(self) -> None:
        percent = 0.1
        with self.sut.crop_pdf(self.TELEGRAM_FILE_ID, percentage=percent) as actual:
            assert actual == self.OUTPUT_PATH
            self.cli_service.crop_pdf_by_percentage.assert_called_once_with(
                self.DOWNLOAD_PATH, self.OUTPUT_PATH, percent
            )
            self._assert_telegram_and_io_services("Cropped")

    def test_crop_pdf_by_margin_size(self) -> None:
        margin_size = 10
        with self.sut.crop_pdf(
            self.TELEGRAM_FILE_ID, margin_size=margin_size
        ) as actual:
            assert actual == self.OUTPUT_PATH
            self.cli_service.crop_pdf_by_margin_size.assert_called_once_with(
                self.DOWNLOAD_PATH, self.OUTPUT_PATH, margin_size
            )
            self._assert_telegram_and_io_services("Cropped")

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    def test_decrypt_pdf(self, num_pages: int) -> None:
        reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        reader.is_encrypted = True

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls:
            reader_cls.return_value = reader
            writer_cls.return_value = writer

            with self.sut.decrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD) as actual:
                assert actual == self.OUTPUT_PATH
                self._assert_telegram_and_io_services("Decrypted")
                reader.decrypt.assert_called_once_with(self.PASSWORD)

                calls = [call(page) for page in pages]
                writer.add_page.assert_has_calls(calls)

    def test_decrypt_pdf_not_encrypted(self) -> None:
        reader = MagicMock(spec=PdfFileReader)
        reader.is_encrypted = False

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls:
            reader_cls.return_value = reader
            with pytest.raises(PdfDecryptError), self.sut.decrypt_pdf(
                self.TELEGRAM_FILE_ID, self.PASSWORD
            ):
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                reader.decrypt.assert_not_called()
                self.io_service.create_temp_pdf_file.assert_not_called()

    def test_decrypt_pdf_incorrect_password(self) -> None:
        reader = MagicMock(spec=PdfFileReader)
        reader.is_encrypted = True
        reader.decrypt.return_value = 0

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls:
            reader_cls.return_value = reader
            with pytest.raises(PdfIncorrectPasswordError), self.sut.decrypt_pdf(
                self.TELEGRAM_FILE_ID, self.PASSWORD
            ):
                self._assert_decrypt_failure(reader)

    def test_decrypt_pdf_invalid_encryption_method(self) -> None:
        reader = MagicMock(spec=PdfFileReader)
        reader.is_encrypted = True
        reader.decrypt.side_effect = NotImplementedError()

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls:
            reader_cls.return_value = reader
            with pytest.raises(PdfDecryptError), self.sut.decrypt_pdf(
                self.TELEGRAM_FILE_ID, self.PASSWORD
            ):
                self._assert_decrypt_failure(reader)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    def test_encrypt_pdf(self, num_pages: int) -> None:
        reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        reader.is_encrypted = False

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls:
            reader_cls.return_value = reader
            writer_cls.return_value = writer

            with self.sut.encrypt_pdf(self.TELEGRAM_FILE_ID, self.PASSWORD) as actual:
                assert actual == self.OUTPUT_PATH
                self._assert_telegram_and_io_services("Encrypted")
                writer.encrypt.assert_called_once_with(self.PASSWORD)

                calls = [call(page) for page in pages]
                writer.add_page.assert_has_calls(calls)

    def test_encrypt_pdf_already_encrypted(self) -> None:
        reader = MagicMock(spec=PdfFileReader)
        reader.is_encrypted = True

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls:
            reader_cls.return_value = reader
            with pytest.raises(PdfEncryptError), self.sut.encrypt_pdf(
                self.TELEGRAM_FILE_ID, self.PASSWORD
            ):
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                self.io_service.create_temp_pdf_file.assert_not_called()

    def test_extract_text_from_pdf(self) -> None:
        with patch("pdf_bot.pdf.pdf_service.extract_text") as extract_text, patch(
            "pdf_bot.pdf.pdf_service.textwrap"
        ), self.sut.extract_text_from_pdf(self.TELEGRAM_FILE_ID) as actual:
            assert actual == self.OUTPUT_PATH
            self.telegram_service.download_pdf_file.assert_called_once_with(
                self.TELEGRAM_FILE_ID
            )
            self.io_service.create_temp_txt_file.assert_called_once_with("PDF_text")
            extract_text.assert_called_once_with(self.DOWNLOAD_PATH)

    def test_extract_text_from_pdf_no_text(self) -> None:
        with patch("pdf_bot.pdf.pdf_service.extract_text") as extract_text:
            extract_text.return_value = ""
            with pytest.raises(PdfNoTextError), self.sut.extract_text_from_pdf(
                self.TELEGRAM_FILE_ID
            ):
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                self.io_service.create_temp_txt_file.assert_not_called()
                extract_text.assert_called_once_with(self.DOWNLOAD_PATH)

    def test_extract_pdf_images(self) -> None:
        with self.sut.extract_pdf_images(self.TELEGRAM_FILE_ID) as actual:
            assert actual == self.DIR_NAME
            self.telegram_service.download_pdf_file.assert_called_once_with(
                self.TELEGRAM_FILE_ID
            )
            self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
            self.cli_service.extract_pdf_images.assert_called_once_with(
                self.DOWNLOAD_PATH, self.DIR_NAME
            )
            self.mock_os.listdir.assert_called_once_with(self.DIR_NAME)

    def test_extract_pdf_images_no_images(self) -> None:
        self.mock_os.listdir.return_value = []

        with pytest.raises(PdfNoImagesError), self.sut.extract_pdf_images(
            self.TELEGRAM_FILE_ID
        ):
            self.telegram_service.download_pdf_file.assert_called_once_with(
                self.TELEGRAM_FILE_ID
            )
            self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
            self.cli_service.extract_pdf_images.assert_called_once_with(
                self.DOWNLOAD_PATH, self.DIR_NAME
            )
            self.mock_os.listdir.assert_called_once_with(self.DIR_NAME)

    def test_extract_pdf_images_cli_error(self) -> None:
        self.cli_service.extract_pdf_images.side_effect = CLIServiceError()

        with pytest.raises(PdfServiceError), self.sut.extract_pdf_images(
            self.TELEGRAM_FILE_ID
        ):
            self.telegram_service.download_pdf_file.assert_called_once_with(
                self.TELEGRAM_FILE_ID
            )
            self.io_service.create_temp_directory.assert_called_once_with("PDF_images")
            self.cli_service.extract_pdf_images.assert_called_once_with(
                self.DOWNLOAD_PATH, self.DIR_NAME
            )
            self.mock_os.listdir.assert_not_called()

    @pytest.mark.parametrize("num_files", [0, 1, 2, 5])
    def test_merge_pdfs(self, num_files: int) -> None:
        file_data_list, file_ids, file_paths = self._get_file_data_list(num_files)
        merger = MagicMock(spec=PdfFileMerger)
        self.telegram_service.download_files.return_value.__enter__.return_value = (
            file_paths
        )

        with patch("pdf_bot.pdf.pdf_service.PdfFileMerger") as merger_cls:
            merger_cls.return_value = merger
            with self.sut.merge_pdfs(file_data_list):
                self.telegram_service.download_files.assert_called_once_with(file_ids)
                calls = [call(x) for x in file_paths]
                merger.append.assert_has_calls(calls)
                self.io_service.create_temp_pdf_file.assert_called_once_with(
                    "Merged_files"
                )
                merger.write.assert_called_once()

    @pytest.mark.parametrize("exception", [PyPdfReadError(), ValueError()])
    def test_merge_pdfs_read_error(self, exception: Exception) -> None:
        file_data_list, file_ids, file_paths = self._get_file_data_list(2)
        merger = MagicMock(spec=PdfFileMerger)
        merger.append.side_effect = exception
        self.telegram_service.download_files.return_value.__enter__.return_value = (
            file_paths
        )

        with patch("pdf_bot.pdf.pdf_service.PdfFileMerger") as merger_cls:
            merger_cls.return_value = merger
            with pytest.raises(PdfReadError), self.sut.merge_pdfs(file_data_list):
                self.telegram_service.download_files.assert_called_once_with(file_ids)
                self.io_service.create_temp_pdf_file.assert_not_called()
                merger.write.assert_not_called()

    def test_ocr_pdf(self) -> None:
        with patch("pdf_bot.pdf.pdf_service.ocrmypdf") as ocrmypdf, self.sut.ocr_pdf(
            self.TELEGRAM_FILE_ID
        ) as actual:
            assert actual == self.OUTPUT_PATH
            self._assert_telegram_and_io_services("OCR")
            ocrmypdf.ocr.assert_called_once_with(
                self.DOWNLOAD_PATH, self.OUTPUT_PATH, progress_bar=False
            )

    def test_ocr_pdf_prior_ocr_found(self) -> None:
        with patch("pdf_bot.pdf.pdf_service.ocrmypdf") as ocrmypdf:
            ocrmypdf.ocr.side_effect = PriorOcrFoundError()
            with pytest.raises(PdfOcrError), self.sut.ocr_pdf(self.TELEGRAM_FILE_ID):
                self._assert_telegram_and_io_services("OCR")
                ocrmypdf.ocr.assert_called_once_with(
                    self.DOWNLOAD_PATH, self.OUTPUT_PATH, progress_bar=False
                )

    def test_preview_pdf(self) -> None:
        pdf_path = "pdf_path"
        out_path = "out_path"

        reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        page = MagicMock(spec=PageObject)
        reader.is_encrypted = False
        reader.pages = [page]

        image = MagicMock()

        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = (
            pdf_path
        )
        self.io_service.create_temp_png_file.return_value.__enter__.return_value = (
            out_path
        )

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls, patch("pdf_bot.pdf.pdf_service.pdf2image") as pdf2image:
            reader_cls.return_value = reader
            writer_cls.return_value = writer
            pdf2image.convert_from_path.return_value = [image]

            with self.sut.preview_pdf(self.TELEGRAM_FILE_ID) as actual:
                assert actual == out_path
                self.telegram_service.download_pdf_file.assert_called_once_with(
                    self.TELEGRAM_FILE_ID
                )
                writer.add_page.assert_called_once_with(page)
                pdf2image.convert_from_path.assert_called_once_with(pdf_path, fmt="png")
                image.save.assert_called_once_with(out_path)

    def test_rename_pdf(self) -> None:
        file_name = "file_name"
        self.mock_os.path.join.return_value = self.OUTPUT_PATH

        with patch("pdf_bot.pdf.pdf_service.shutil") as shutil, self.sut.rename_pdf(
            self.TELEGRAM_FILE_ID, file_name
        ) as actual:
            assert actual == self.OUTPUT_PATH
            self.telegram_service.download_pdf_file.assert_called_once_with(
                self.TELEGRAM_FILE_ID
            )
            self.io_service.create_temp_directory.assert_called_once()
            self.mock_os.path.join.assert_called_once_with(self.DIR_NAME, file_name)
            shutil.copy.assert_called_once_with(self.DOWNLOAD_PATH, self.OUTPUT_PATH)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    def test_rotate_pdf(self, num_pages: int) -> None:
        degree = 90
        reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        reader.is_encrypted = False

        pages = [MagicMock(spec=PageObject) for _ in range(num_pages)]
        rotated_pages = [MagicMock() for _ in pages]
        for i, page in enumerate(pages):
            page.rotate_clockwise.return_value = rotated_pages[i]
        reader.pages = pages

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls:
            reader_cls.return_value = reader
            writer_cls.return_value = writer

            with self.sut.rotate_pdf(self.TELEGRAM_FILE_ID, degree) as actual:
                assert actual == self.OUTPUT_PATH
                self._assert_telegram_and_io_services("Rotated")

                for page in pages:
                    page.rotate_clockwise.assert_called_once_with(degree)

                calls = [call(page) for page in rotated_pages]
                writer.add_page.assert_has_calls(calls)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    def test_scale_pdf_by_factor(self, num_pages: int) -> None:
        scale_data = ScaleByData(1, 2)

        reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        reader.is_encrypted = False

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls:
            reader_cls.return_value = reader
            writer_cls.return_value = writer

            with self.sut.scale_pdf(self.TELEGRAM_FILE_ID, scale_data) as actual:
                assert actual == self.OUTPUT_PATH
                self._assert_telegram_and_io_services("Scaled")

                calls = []
                for page in pages:
                    page.scale.assert_called_once_with(scale_data.x, scale_data.y)
                    calls.append(call(page))
                writer.add_page.assert_has_calls(calls)

    @pytest.mark.parametrize("num_pages", [0, 1, 2, 5])
    def test_scale_pdf_to_dimension(self, num_pages: int) -> None:
        scale_data = ScaleToData(1, 2)

        reader = MagicMock(spec=PdfFileReader)
        writer = MagicMock(spec=PdfFileWriter)
        reader.is_encrypted = False

        pages = [MagicMock() for _ in range(num_pages)]
        reader.pages = pages

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileWriter"
        ) as writer_cls:
            reader_cls.return_value = reader
            writer_cls.return_value = writer

            with self.sut.scale_pdf(self.TELEGRAM_FILE_ID, scale_data) as actual:
                assert actual == self.OUTPUT_PATH
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
    def test_split_range_valid(self, split_range: str) -> None:
        assert self.sut.split_range_valid(split_range) is True

    def test_split_range_invalid(self) -> None:
        assert self.sut.split_range_valid("clearly_invalid") is False

    def test_split_pdf(self) -> None:
        split_range = "7:"
        reader = MagicMock(spec=PdfFileReader)
        merger = MagicMock(spec=PdfFileMerger)
        reader.is_encrypted = False

        with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as reader_cls, patch(
            "pdf_bot.pdf.pdf_service.PdfFileMerger"
        ) as merger_cls:
            reader_cls.return_value = reader
            merger_cls.return_value = merger

            with self.sut.split_pdf(self.TELEGRAM_FILE_ID, split_range) as actual:
                assert actual == self.OUTPUT_PATH
                self._assert_telegram_and_io_services("Split")
                merger.append.assert_called_once_with(
                    reader, pages=PageRange(split_range)
                )

    @staticmethod
    def _context_manager_side_effect_echo(
        return_value: str, *_args: Any, **_kwargs: Any
    ) -> MagicMock:
        mock = MagicMock()
        mock.__enter__.return_value = return_value
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
        self.telegram_service.download_pdf_file.assert_called_once_with(
            self.TELEGRAM_FILE_ID
        )
        self.io_service.create_temp_pdf_file.assert_called_once_with(
            temp_pdf_file_prefix
        )

    def _assert_decrypt_failure(self, reader: MagicMock) -> None:
        self.telegram_service.download_pdf_file.assert_called_once_with(
            self.TELEGRAM_FILE_ID
        )
        reader.decrypt.assert_called_once_with(self.PASSWORD)
        self.io_service.create_temp_pdf_file.assert_not_called()
