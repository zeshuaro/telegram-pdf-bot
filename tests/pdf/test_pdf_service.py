import os
from random import randint
from typing import Callable, List, cast
from unittest.mock import ANY, MagicMock, call, patch

import pytest
from ocrmypdf.exceptions import PriorOcrFoundError
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from PyPDF2.errors import PdfReadError as PyPdfReadError
from PyPDF2.pagerange import PageRange

from pdf_bot.cli import CLIService
from pdf_bot.compare import CompareService
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
    PdfNoTextError,
)
from pdf_bot.telegram import TelegramService


@pytest.fixture(name="telegram_service")
def fixture_telegram_service() -> TelegramService:
    return cast(TelegramService, MagicMock())


@pytest.fixture(name="pdf_service")
def fixture_pdf_service(
    cli_service: CLIService, io_service: IOService, telegram_service: TelegramService
) -> CompareService:
    return PdfService(cli_service, io_service, telegram_service)


def test_add_watermark_to_pdf(
    pdf_service: PdfService,
    telegram_service: TelegramService,
    io_service: IOService,
    document_ids_generator: Callable[[int], List[str]],
    context_manager_side_effect_echo: Callable[[str], MagicMock],
    method_side_effect_echo: Callable[[str], MagicMock],
):
    src_file_id, wmk_file_id = document_ids_generator(2)
    src_reader = cast(PdfFileReader, MagicMock())
    wmk_reader = cast(PdfFileReader, MagicMock())
    writer = cast(PdfFileWriter, MagicMock())
    src_reader.is_encrypted = wmk_reader.is_encrypted = False

    src_pages = [MagicMock() for _ in range(randint(2, 10))]
    src_reader.pages = src_pages

    wmk_page = MagicMock()
    wmk_reader.pages = [wmk_page]

    def pdf_file_reader_side_effect(file_id: str, *_args, **_kwargs):
        if file_id == src_file_id:
            return src_reader
        return wmk_reader

    with patch("builtins.open") as mock_open, patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileWriter"
    ) as pdf_file_writer:
        telegram_service.download_file.side_effect = context_manager_side_effect_echo
        mock_open.side_effect = method_side_effect_echo
        pdf_file_reader.side_effect = pdf_file_reader_side_effect
        pdf_file_writer.return_value = writer

        with pdf_service.add_watermark_to_pdf(src_file_id, wmk_file_id):
            add_page_calls = []
            for src_page in src_pages:
                src_page.merge_page.assert_called_once_with(wmk_page)
                add_page_calls.append(call(src_page))

            writer.add_page.assert_has_calls(add_page_calls)
            writer.write.assert_called_once()
            io_service.create_temp_pdf_file.assert_called_once_with(
                prefix="File_with_watermark"
            )


def test_add_watermark_to_pdf_read_error(pdf_service: PdfService):
    file_id = "file_id"
    with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as pdf_file_reader:
        pdf_file_reader.side_effect = PyPdfReadError()
        with pytest.raises(PdfReadError), pdf_service.add_watermark_to_pdf(
            file_id, file_id
        ):
            pass


def test_black_and_white_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    images = "images"

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.pdf2image"
    ) as pdf2image, patch("pdf_bot.pdf.pdf_service.img2pdf") as img2pdf:
        pdf2image.convert_from_path.return_value = images
        with pdf_service.black_and_white_pdf(file_id):
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with(
                prefix="Black_and_White"
            )
            pdf2image.convert_from_path.assert_called_once()
            img2pdf.convert.assert_called_once_with(images)


def test_beautify_and_convert_images_to_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
    file_data_generator: Callable[[int], List[FileData]],
):
    num_files = randint(2, 10)
    file_data_list = file_data_generator(num_files)
    file_ids = [x.id for x in file_data_list]
    telegram_service.download_files.return_value.__enter__.return_value = file_ids

    with patch(
        "pdf_bot.pdf.pdf_service.noteshrink"
    ) as noteshrink, pdf_service.beautify_and_convert_images_to_pdf(file_data_list):
        telegram_service.download_files.assert_called_once_with(file_ids)
        io_service.create_temp_pdf_file.assert_called_once_with(prefix="Beautified")
        noteshrink.notescan_main.assert_called_once_with(
            file_ids, basename=ANY, pdfname=ANY
        )


def test_compress_pdf(
    pdf_service: PdfService,
    cli_service: CLIService,
    telegram_service: TelegramService,
    io_service: IOService,
):
    file_id = "file_id"
    file_path = "file_path"
    out_path = "out_path"

    old_size = randint(11, 20)
    new_size = randint(1, 10)

    def getsize_side_effect(path: str, *_args, **_kwargs):
        if path == file_path:
            return old_size
        return new_size

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.pdf.pdf_service.os") as mock_os:
        mock_os.path.getsize.side_effect = getsize_side_effect
        with pdf_service.compress_pdf(file_id) as compress_result:
            assert compress_result == CompressResult(old_size, new_size, out_path)
            cli_service.compress_pdf.assert_called_once_with(file_path, out_path)
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with(prefix="Compressed")


def test_convert_images_to_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
    file_data_generator: Callable[[int], List[FileData]],
):
    num_files = randint(2, 10)
    file_data_list = file_data_generator(num_files)
    file_ids = [x.id for x in file_data_list]
    telegram_service.download_files.return_value.__enter__.return_value = file_ids

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.img2pdf"
    ) as img2pdf, pdf_service.convert_images_to_pdf(file_data_list):
        telegram_service.download_files.assert_called_once_with(file_ids)
        io_service.create_temp_pdf_file.assert_called_once_with(prefix="Converted")
        img2pdf.convert.assert_called_once_with(file_ids)


def test_create_pdf_from_text(pdf_service: PdfService):
    text = "text"
    font_data = FontData("family", "url")
    html_doc = MagicMock()

    with patch("pdf_bot.pdf.pdf_service.HTML") as html_class, patch(
        "pdf_bot.pdf.pdf_service.CSS"
    ) as css_class:
        html_class.return_value = html_doc
        with pdf_service.create_pdf_from_text(text, font_data):
            html_doc.write_pdf.assert_called_once()
            css_class.assert_called_once()


def test_create_pdf_from_text_without_font_data(pdf_service: PdfService):
    text = "text"
    html_doc = MagicMock()

    with patch("pdf_bot.pdf.pdf_service.HTML") as html_class, patch(
        "pdf_bot.pdf.pdf_service.CSS"
    ) as css_class:
        html_class.return_value = html_doc
        with pdf_service.create_pdf_from_text(text, None):
            html_doc.write_pdf.assert_called_once()
            css_class.assert_not_called()


def test_drop_pdf_by_percentage(
    pdf_service: PdfService,
    io_service: IOService,
    cli_service: CLIService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    percent = randint(1, 10)
    file_path = "file_path"
    out_path = "out_path"

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with pdf_service.crop_pdf(file_id, percentage=percent) as actual_path:
        assert actual_path == out_path
        cli_service.crop_pdf_by_percentage.assert_called_once_with(
            file_path, out_path, percent
        )
        telegram_service.download_file.assert_called_once_with(file_id)
        io_service.create_temp_pdf_file.assert_called_once_with(prefix="Cropped")


def test_crop_pdf_by_margin_size(
    pdf_service: PdfService,
    io_service: IOService,
    cli_service: CLIService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    margin_size = randint(1, 10)
    file_path = "file_path"
    out_path = "out_path"

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with pdf_service.crop_pdf(file_id, margin_size=margin_size) as actual_path:
        assert actual_path == out_path
        cli_service.crop_pdf_by_margin_size.assert_called_once_with(
            file_path, out_path, margin_size
        )
        telegram_service.download_file.assert_called_once_with(file_id)
        io_service.create_temp_pdf_file.assert_called_once_with(prefix="Cropped")


def test_compare_pdfs(
    pdf_service: PdfService,
    telegram_service: TelegramService,
    document_ids_generator: Callable[[int], List[str]],
):
    doc_ids = document_ids_generator(2)
    with patch(
        "pdf_bot.pdf.pdf_service.pdf_diff"
    ) as pdf_diff, pdf_service.compare_pdfs(*doc_ids):
        assert pdf_diff.main.called
        calls = [call(doc_id) for doc_id in doc_ids]
        telegram_service.download_file.assert_has_calls(calls, any_order=True)


def test_decrypt_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    password = "password"
    out_path = "out_path"

    reader = cast(PdfFileReader, MagicMock())
    writer = cast(PdfFileWriter, MagicMock())
    reader.is_encrypted = True

    pages = [MagicMock() for _ in range(randint(2, 10))]
    reader.pages = pages

    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileWriter"
    ) as pdf_file_writer:
        pdf_file_reader.return_value = reader
        pdf_file_writer.return_value = writer

        with pdf_service.decrypt_pdf(file_id, password) as actual_path:
            assert actual_path == out_path
            telegram_service.download_file.assert_called_once_with(file_id)
            reader.decrypt.assert_called_once_with(password)
            io_service.create_temp_pdf_file.assert_called_once_with("Decrypted")

            calls = [call(page) for page in pages]
            writer.add_page.assert_has_calls(calls)


def test_decrypt_pdf_already_encrypted(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    password = "password"

    reader = cast(PdfFileReader, MagicMock())
    reader.is_encrypted = False

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader:
        pdf_file_reader.return_value = reader
        with pytest.raises(PdfDecryptError), pdf_service.decrypt_pdf(file_id, password):
            telegram_service.download_file.assert_called_once_with(file_id)
            reader.decrypt.assert_not_called()
            io_service.create_temp_pdf_file.assert_not_called()


def test_decrypt_pdf_incorrect_password(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    password = "password"

    reader = cast(PdfFileReader, MagicMock())
    reader.is_encrypted = True
    reader.decrypt.return_value = 0

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader:
        pdf_file_reader.return_value = reader
        with pytest.raises(PdfIncorrectPasswordError), pdf_service.decrypt_pdf(
            file_id, password
        ):
            telegram_service.download_file.assert_called_once_with(file_id)
            reader.decrypt.assert_called_once_with(password)
            io_service.create_temp_pdf_file.assert_not_called()


def test_decrypt_pdf_invalid_encryption_method(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    password = "password"

    reader = cast(PdfFileReader, MagicMock())
    reader.is_encrypted = True
    reader.decrypt.side_effect = NotImplementedError()

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader:
        pdf_file_reader.return_value = reader
        with pytest.raises(PdfDecryptError), pdf_service.decrypt_pdf(file_id, password):
            telegram_service.download_file.assert_called_once_with(file_id)
            reader.decrypt.assert_called_once_with(password)
            io_service.create_temp_pdf_file.assert_not_called()


def test_encrypt_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    password = "password"
    out_path = "out_path"

    reader = cast(PdfFileReader, MagicMock())
    writer = cast(PdfFileWriter, MagicMock())
    reader.is_encrypted = False

    pages = [MagicMock() for _ in range(randint(2, 10))]
    reader.pages = pages

    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileWriter"
    ) as pdf_file_writer:
        pdf_file_reader.return_value = reader
        pdf_file_writer.return_value = writer

        with pdf_service.encrypt_pdf(file_id, password) as actual_path:
            assert actual_path == out_path
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with("Encrypted")

            calls = [call(page) for page in pages]
            writer.add_page.assert_has_calls(calls)
            writer.encrypt.assert_called_once_with(password)


def test_encrypt_pdf_already_encrypted(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    password = "password"

    reader = cast(PdfFileReader, MagicMock())
    reader.is_encrypted = True

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader:
        pdf_file_reader.return_value = reader
        with pytest.raises(PdfEncryptError), pdf_service.encrypt_pdf(file_id, password):
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_not_called()


def test_extract_text_from_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    file_path = "file_path"
    telegram_service.download_file.return_value.__enter__.return_value = file_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.extract_text"
    ) as extract_text, patch(
        "pdf_bot.pdf.pdf_service.textwrap"
    ), pdf_service.extract_text_from_pdf(
        file_id
    ):
        telegram_service.download_file.assert_called_once_with(file_id)
        extract_text.assert_called_once_with(file_path)
        io_service.create_temp_txt_file.assert_called_once_with("PDF_text")


def test_extract_text_from_pdf_no_text(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    file_path = "file_path"
    telegram_service.download_file.return_value.__enter__.return_value = file_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.extract_text"
    ) as extract_text:
        extract_text.return_value = ""
        with pytest.raises(PdfNoTextError), pdf_service.extract_text_from_pdf(file_id):
            telegram_service.download_file.assert_called_once_with(file_id)
            extract_text.assert_called_once_with(file_path)
            io_service.create_temp_txt_file.assert_not_called()


def test_merge_pdfs(
    pdf_service: PdfService,
    telegram_service: TelegramService,
    file_data_generator: Callable[[int], List[FileData]],
):
    num_files = randint(2, 10)
    file_data_list = file_data_generator(num_files)
    file_ids = [x.id for x in file_data_list]

    telegram_service.download_files.return_value.__enter__.return_value = file_ids
    merger = MagicMock()

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileMerger"
    ) as pdf_file_merger:
        pdf_file_merger.return_value = merger
        with pdf_service.merge_pdfs(file_data_list):
            telegram_service.download_files.assert_called_once_with(file_ids)
            calls = [call(ANY) for _ in range(num_files)]
            merger.append.assert_has_calls(calls)
            merger.write.assert_called_once()


@pytest.mark.parametrize("exception", [(PyPdfReadError()), (ValueError(),)])
def test_merge_pdfs_read_error(
    pdf_service: PdfService,
    telegram_service: TelegramService,
    file_data_generator: Callable[[int], List[FileData]],
    exception: Exception,
):
    num_files = randint(1, 10)
    file_data_list = file_data_generator(num_files)
    file_ids = [x.id for x in file_data_list]

    telegram_service.download_files.return_value.__enter__.return_value = file_ids
    merger = cast(PdfFileMerger, MagicMock())
    merger.append.side_effect = exception

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileMerger"
    ) as pdf_file_merger:
        pdf_file_merger.return_value = merger
        with pytest.raises(PdfReadError), pdf_service.merge_pdfs(file_data_list):
            telegram_service.download_files.assert_called_once_with(file_ids)
            merger.write.assert_not_called()


def test_ocr_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    file_path = "file_path"
    out_path = "out_path"

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.pdf.pdf_service.ocrmypdf") as ocrmypdf, pdf_service.ocr_pdf(
        file_id
    ) as actual_path:
        assert actual_path == out_path
        telegram_service.download_file.assert_called_once_with(file_id)
        io_service.create_temp_pdf_file.assert_called_once_with("OCR")
        ocrmypdf.ocr.assert_called_once_with(file_path, out_path, progress_bar=False)


def test_ocr_pdf_prior_ocr_found(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    file_path = "file_path"
    out_path = "out_path"

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.pdf.pdf_service.ocrmypdf") as ocrmypdf:
        ocrmypdf.ocr.side_effect = PriorOcrFoundError()
        with pytest.raises(PdfOcrError), pdf_service.ocr_pdf(file_id):
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with("OCR")
            ocrmypdf.ocr.assert_called_once_with(
                file_path, out_path, progress_bar=False
            )


def test_rename_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    file_name = "file_name"
    file_path = "file_path"
    dir_name = "dir_name"
    out_path = os.path.join(dir_name, file_name)

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_directory.return_value.__enter__.return_value = dir_name

    with patch("pdf_bot.pdf.pdf_service.shutil") as shutil, pdf_service.rename_pdf(
        file_id, file_name
    ) as actual_path:
        assert actual_path == out_path

        telegram_service.download_file.assert_called_once_with(file_id)
        io_service.create_temp_directory.assert_called_once()
        shutil.copy.assert_called_once_with(file_path, out_path)


def test_rotate_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    degree = 90
    out_path = "out_path"

    reader = cast(PdfFileReader, MagicMock())
    writer = cast(PdfFileWriter, MagicMock())
    reader.is_encrypted = False

    pages = [MagicMock() for _ in range(randint(2, 10))]
    rotated_pages = [MagicMock() for _ in pages]
    for i, page in enumerate(pages):
        page.rotate_clockwise.return_value = rotated_pages[i]
    reader.pages = pages

    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileWriter"
    ) as pdf_file_writer:
        pdf_file_reader.return_value = reader
        pdf_file_writer.return_value = writer

        with pdf_service.rotate_pdf(file_id, degree) as actual_path:
            assert actual_path == out_path
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with("Rotated")

            for page in pages:
                page.rotate_clockwise.assert_called_once_with(degree)

            calls = [call(page) for page in rotated_pages]
            writer.add_page.assert_has_calls(calls)


def test_scale_pdf_by_factor(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    out_path = "out_path"
    scale_data = ScaleByData(randint(0, 10), randint(0, 10))

    reader = cast(PdfFileReader, MagicMock())
    writer = cast(PdfFileWriter, MagicMock())
    reader.is_encrypted = False

    pages = [MagicMock() for _ in range(randint(2, 10))]
    reader.pages = pages

    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileWriter"
    ) as pdf_file_writer:
        pdf_file_reader.return_value = reader
        pdf_file_writer.return_value = writer

        with pdf_service.scale_pdf(file_id, scale_data) as actual_path:
            assert actual_path == out_path
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with("Scaled")

            calls = []
            for page in pages:
                page.scale.assert_called_once_with(scale_data.x, scale_data.y)
                calls.append(call(page))
            writer.add_page.assert_has_calls(calls)


def test_scale_pdf_to_dimension(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    out_path = "out_path"
    scale_data = ScaleToData(randint(0, 10), randint(0, 10))

    reader = cast(PdfFileReader, MagicMock())
    writer = cast(PdfFileWriter, MagicMock())
    reader.is_encrypted = False

    pages = [MagicMock() for _ in range(randint(2, 10))]
    reader.pages = pages

    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileWriter"
    ) as pdf_file_writer:
        pdf_file_reader.return_value = reader
        pdf_file_writer.return_value = writer

        with pdf_service.scale_pdf(file_id, scale_data) as actual_path:
            assert actual_path == out_path
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with("Scaled")

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
def test_split_range_valid(pdf_service: PdfService, split_range: str):
    assert pdf_service.split_range_valid(split_range)


def test_split_range_invalid(pdf_service: PdfService):
    assert not pdf_service.split_range_valid("clearly_invalid")


def test_split_pdf(
    pdf_service: PdfService,
    io_service: IOService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    out_path = "out_path"
    split_range = "7:"

    reader = cast(PdfFileReader, MagicMock())
    merger = cast(PdfFileMerger, MagicMock())
    reader.is_encrypted = False

    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with patch("builtins.open"), patch(
        "pdf_bot.pdf.pdf_service.PdfFileReader"
    ) as pdf_file_reader, patch(
        "pdf_bot.pdf.pdf_service.PdfFileMerger"
    ) as pdf_file_merger:
        pdf_file_reader.return_value = reader
        pdf_file_merger.return_value = merger

        with pdf_service.split_pdf(file_id, split_range) as actual_path:
            assert actual_path == out_path
            telegram_service.download_file.assert_called_once_with(file_id)
            io_service.create_temp_pdf_file.assert_called_once_with("Split")
            merger.append.assert_called_once_with(reader, pages=PageRange(split_range))
