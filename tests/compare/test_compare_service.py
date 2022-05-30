from typing import Iterator
from unittest.mock import patch

import pytest
from pdf_diff import NoDifferenceError
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.compare import CompareService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError

WAIT_FIRST_PDF = 0
WAIT_SECOND_PDF = 1
COMPARE_ID = "compare_id"


@pytest.fixture(name="compare_service")
def fixture_compare_service(
    pdf_service: PdfService, telegram_service: TelegramService
) -> CompareService:
    return CompareService(pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.compare.compare_service.set_lang"):
        yield


def test_ask_first_pdf(
    compare_service: CompareService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = compare_service.ask_first_pdf(telegram_update, telegram_context)
    assert actual == WAIT_FIRST_PDF
    telegram_update.effective_message.reply_text.assert_called_once()


def test_check_first_pdf(
    compare_service: CompareService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: str,
):
    actual = compare_service.check_first_pdf(telegram_update, telegram_context)
    assert actual == WAIT_SECOND_PDF
    telegram_context.user_data.__setitem__.assert_called_with(COMPARE_ID, document_id)


def test_check_first_pdf_invalid_pdf(
    compare_service: CompareService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.check_pdf_document.side_effect = TelegramServiceError()

    actual = compare_service.check_first_pdf(telegram_update, telegram_context)

    assert actual == WAIT_FIRST_PDF
    telegram_context.user_data.__setitem__.assert_not_called()


def test_compare_pdfs(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.compare.compare_service.check_user_data"), patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        out_fn = "output"
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.compare_pdfs.return_value.__enter__.return_value = out_fn

        actual = compare_service.compare_pdfs(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.compare_pdfs.assert_called_with(document_id, document_id)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_fn, TaskType.compare_pdf
        )


def test_compare_pdfs_no_differences(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.compare.compare_service.check_user_data"), patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.compare_pdfs.return_value.__enter__.side_effect = (
            NoDifferenceError()
        )

        actual = compare_service.compare_pdfs(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.compare_pdfs.assert_called_with(document_id, document_id)
        send_result_file.assert_not_called()


def test_compare_pdfs_invalid_user_data(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    with patch(
        "pdf_bot.compare.compare_service.check_user_data"
    ) as check_user_data, patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        check_user_data.return_value = False

        actual = compare_service.compare_pdfs(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.compare_pdfs.assert_not_called()
        send_result_file.assert_not_called()


def test_check_second_pdf_invalid_pdf(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    with patch("pdf_bot.compare.compare_service.check_user_data"), patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = compare_service.compare_pdfs(telegram_update, telegram_context)

        assert actual == WAIT_SECOND_PDF
        pdf_service.compare_pdfs.assert_not_called()
        send_result_file.assert_not_called()
