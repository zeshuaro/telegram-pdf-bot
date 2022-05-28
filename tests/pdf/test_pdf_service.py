import os
from pathlib import Path
from random import randint
from typing import Callable, List, cast
from unittest.mock import ANY, MagicMock, call, patch

import pytest
from PyPDF2.utils import PdfReadError as PyPdfReadError

from pdf_bot.compare import CompareService
from pdf_bot.io.io_service import IOService
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfReadError, PdfService
from pdf_bot.telegram import TelegramService
from pdf_bot.text import FontData


@pytest.fixture(name="telegram_service")
def fixture_telegram_service() -> TelegramService:
    return cast(TelegramService, MagicMock())


@pytest.fixture(name="pdf_service")
def fixture_pdf_service(
    io_service: IOService, telegram_service: TelegramService
) -> CompareService:
    return PdfService(io_service, telegram_service)


def test_add_watermark_to_pdf(
    pdf_service: PdfService,
    telegram_service: TelegramService,
    get_data_file: Callable[[str], Path],
    context_manager_side_effect: Callable[[str], MagicMock],
):
    telegram_service.download_file.side_effect = context_manager_side_effect
    src_file = get_data_file("base.pdf")
    wmk_file = get_data_file("watermark.pdf")
    expected_file = get_data_file("base_watermark.pdf")

    with pdf_service.add_watermark_to_pdf(src_file, wmk_file) as out_fn:
        assert os.path.getsize(out_fn) == os.path.getsize(expected_file)


def test_add_watermark_to_pdf_read_error(pdf_service: PdfService):
    file_id = "file_id"
    with patch("pdf_bot.pdf.pdf_service.PdfFileReader") as pdf_file_reader:
        pdf_file_reader.side_effect = PyPdfReadError()
        with pytest.raises(PdfReadError), pdf_service.add_watermark_to_pdf(
            file_id, file_id
        ):
            pass


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
    num_files = randint(0, 10)
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
