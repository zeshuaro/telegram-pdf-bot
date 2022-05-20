from typing import Iterator, cast
from unittest.mock import MagicMock, patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.compare.constants import WAIT_SECOND_PDF
from pdf_bot.consts import PDF_INVALID_FORMAT, PDF_OK, PDF_TOO_LARGE
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.watermark import WatermarkService

WAIT_SOURCE_PDF = 0
WAIT_WATERMARK_PDF = 1
WATERMARK_KEY = "watermark"


@pytest.fixture(name="pdf_service")
def fixture_pdf_service() -> PdfService:
    return cast(PdfService, MagicMock())


@pytest.fixture(name="watermark_service")
def fixture_watermark_service(pdf_service: PdfService) -> WatermarkService:
    return WatermarkService(pdf_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.watermark.watermark_service.set_lang"):
        yield


def test_ask_source_pdf(
    watermark_service: WatermarkService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = watermark_service.ask_source_pdf(telegram_update, telegram_context)
    assert actual == WAIT_SOURCE_PDF


def test_check_source_pdf(
    watermark_service: WatermarkService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.watermark.watermark_service.check_pdf") as check_pdf:
        check_pdf.return_value = PDF_OK

        actual = watermark_service.check_source_pdf(telegram_update, telegram_context)

        assert actual == WAIT_SECOND_PDF
        telegram_context.user_data.__setitem__.assert_called_with(
            WATERMARK_KEY, document_id
        )


@pytest.mark.parametrize(
    "check_pdf_result,expected",
    [(PDF_INVALID_FORMAT, WAIT_SOURCE_PDF), (PDF_TOO_LARGE, ConversationHandler.END)],
)
def test_check_source_pdf_invalid_pdf(
    watermark_service: WatermarkService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    check_pdf_result: int,
    expected: int,
):
    with patch("pdf_bot.watermark.watermark_service.check_pdf") as check_pdf:
        check_pdf.return_value = check_pdf_result

        actual = watermark_service.check_source_pdf(telegram_update, telegram_context)

        assert actual == expected
        telegram_context.user_data.__setitem__.assert_not_called()


def test_check_watermark_pdf(
    watermark_service: WatermarkService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.watermark.watermark_service.check_pdf") as check_pdf, patch(
        "pdf_bot.watermark.watermark_service.check_user_data"
    ) as _check_user_data, patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        check_pdf.return_value = PDF_OK
        out_fn = "output"
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.add_watermark_to_pdf.return_value.__enter__.return_value = out_fn

        actual = watermark_service.check_watermark_pdf(
            telegram_update, telegram_context
        )

        assert actual == ConversationHandler.END
        pdf_service.add_watermark_to_pdf.assert_called_with(document_id, document_id)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_fn, TaskType.watermark_pdf
        )


def test_check_watermark_pdf_service_error(
    watermark_service: WatermarkService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.watermark.watermark_service.check_pdf") as check_pdf, patch(
        "pdf_bot.watermark.watermark_service.check_user_data"
    ) as _check_user_data, patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        check_pdf.return_value = PDF_OK
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.add_watermark_to_pdf.return_value.__enter__.side_effect = (
            PdfServiceError()
        )

        actual = watermark_service.check_watermark_pdf(
            telegram_update, telegram_context
        )

        assert actual == ConversationHandler.END
        pdf_service.add_watermark_to_pdf.assert_called_with(document_id, document_id)
        send_result_file.assert_not_called()


def test_check_watermark_pdf_invalid_user_data(
    watermark_service: WatermarkService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    with patch(
        "pdf_bot.watermark.watermark_service.check_user_data"
    ) as check_user_data, patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        check_user_data.return_value = False

        actual = watermark_service.check_watermark_pdf(
            telegram_update, telegram_context
        )

        assert actual == ConversationHandler.END
        pdf_service.add_watermark_to_pdf.assert_not_called()
        send_result_file.assert_not_called()


@pytest.mark.parametrize(
    "check_pdf_result,expected",
    [(PDF_INVALID_FORMAT, WAIT_SECOND_PDF), (PDF_TOO_LARGE, ConversationHandler.END)],
)
def test_check_watermark_pdf_invalid_pdf(
    watermark_service: WatermarkService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    check_pdf_result: int,
    expected: int,
):
    with patch("pdf_bot.watermark.watermark_service.check_pdf") as check_pdf, patch(
        "pdf_bot.watermark.watermark_service.check_user_data"
    ) as _check_user_data, patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        check_pdf.return_value = check_pdf_result

        actual = watermark_service.check_watermark_pdf(
            telegram_update, telegram_context
        )

        assert actual == expected
        pdf_service.add_watermark_to_pdf.assert_not_called()
        send_result_file.assert_not_called()
