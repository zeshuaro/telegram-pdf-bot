from random import randint
from typing import Callable, List, cast
from unittest.mock import ANY, MagicMock, call, patch

import pytest
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from PyPDF2.errors import PdfReadError as PyPdfReadError

from pdf_bot.cli import CLIService
from pdf_bot.compare import CompareService
from pdf_bot.io.io_service import IOService
from pdf_bot.models import FileData
from pdf_bot.pdf import CompressResult, PdfReadError, PdfService
from pdf_bot.telegram import TelegramService
from pdf_bot.text import FontData


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

    with patch("pdf_bot.pdf.pdf_service.os") as os:
        os.path.getsize.side_effect = getsize_side_effect
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


def test_drop_pdf_by_offset(
    pdf_service: PdfService,
    io_service: IOService,
    cli_service: CLIService,
    telegram_service: TelegramService,
):
    file_id = "file_id"
    offset = randint(1, 10)
    file_path = "file_path"
    out_path = "out_path"

    telegram_service.download_file.return_value.__enter__.return_value = file_path
    io_service.create_temp_pdf_file.return_value.__enter__.return_value = out_path

    with pdf_service.crop_pdf(file_id, offset=offset) as actual_path:
        assert actual_path == out_path
        cli_service.crop_pdf_by_offset.assert_called_once_with(
            file_path, out_path, offset
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
