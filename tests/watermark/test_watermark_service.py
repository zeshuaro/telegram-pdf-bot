from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.watermark import WatermarkService

WAIT_SOURCE_PDF = 0
WAIT_WATERMARK_PDF = 1
WATERMARK_KEY = "watermark"


@pytest.fixture(name="watermark_service")
def fixture_watermark_service(
    pdf_service: PdfService, telegram_service: TelegramService
) -> WatermarkService:
    return WatermarkService(pdf_service, telegram_service)


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
    actual = watermark_service.check_source_pdf(telegram_update, telegram_context)

    assert actual == WAIT_WATERMARK_PDF
    telegram_context.user_data.__setitem__.assert_called_with(
        WATERMARK_KEY, document_id
    )


def test_check_source_pdf_invalid_pdf(
    watermark_service: WatermarkService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.check_pdf_document.side_effect = TelegramServiceError()

    actual = watermark_service.check_source_pdf(telegram_update, telegram_context)

    assert actual == WAIT_SOURCE_PDF
    telegram_context.user_data.__setitem__.assert_not_called()


def test_check_watermark_pdf(
    watermark_service: WatermarkService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.watermark.watermark_service.check_user_data"), patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        out_fn = "output"
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.add_watermark_to_pdf.return_value.__enter__.return_value = out_fn

        actual = watermark_service.add_watermark_to_pdf(
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
    with patch("pdf_bot.watermark.watermark_service.check_user_data"), patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.add_watermark_to_pdf.return_value.__enter__.side_effect = (
            PdfServiceError()
        )

        actual = watermark_service.add_watermark_to_pdf(
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

        actual = watermark_service.add_watermark_to_pdf(
            telegram_update, telegram_context
        )

        assert actual == ConversationHandler.END
        pdf_service.add_watermark_to_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_check_watermark_pdf_invalid_pdf(
    watermark_service: WatermarkService,
    telegram_service: TelegramService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    with patch("pdf_bot.watermark.watermark_service.check_user_data"), patch(
        "pdf_bot.watermark.watermark_service.send_result_file"
    ) as send_result_file:
        telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = watermark_service.add_watermark_to_pdf(
            telegram_update, telegram_context
        )

        assert actual == WAIT_WATERMARK_PDF
        pdf_service.add_watermark_to_pdf.assert_not_called()
        send_result_file.assert_not_called()
