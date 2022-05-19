from typing import Iterator, cast
from unittest.mock import MagicMock, patch

import pytest
from pdf_diff import NoDifferenceError
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.compare import WAIT_FIRST_PDF, CompareService
from pdf_bot.compare.constants import COMPARE_ID, WAIT_SECOND_PDF
from pdf_bot.consts import PDF_INVALID_FORMAT, PDF_OK, PDF_TOO_LARGE
from pdf_bot.pdf import PdfService


@pytest.fixture(name="pdf_service")
def fixture_pdf_service() -> PdfService:
    return cast(PdfService, MagicMock())


@pytest.fixture(name="compare_service")
def fixture_compare_service(pdf_service: PdfService) -> CompareService:
    return CompareService(pdf_service)


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
    document_id: int,
):
    with patch("pdf_bot.compare.compare_service.check_pdf") as check_pdf:
        check_pdf.return_value = PDF_OK

        actual = compare_service.check_first_pdf(telegram_update, telegram_context)

        assert actual == WAIT_SECOND_PDF
        telegram_context.user_data.__setitem__.assert_called_with(
            COMPARE_ID, document_id
        )
        telegram_update.effective_message.reply_text.assert_called_once()


@pytest.mark.parametrize(
    "check_pdf_result,expected",
    [(PDF_INVALID_FORMAT, WAIT_FIRST_PDF), (PDF_TOO_LARGE, ConversationHandler.END)],
)
def test_check_first_pdf_invalid_pdf(
    compare_service: CompareService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    check_pdf_result: int,
    expected: int,
):
    with patch("pdf_bot.compare.compare_service.check_pdf") as check_pdf:
        check_pdf.return_value = check_pdf_result

        actual = compare_service.check_first_pdf(telegram_update, telegram_context)

        assert actual == expected
        telegram_context.user_data.__setitem__.assert_not_called()
        telegram_update.effective_message.reply_text.assert_not_called()


def test_check_second_pdf(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.compare.compare_service.check_pdf") as check_pdf, patch(
        "pdf_bot.compare.compare_service.check_user_data"
    ) as _check_user_data, patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        check_pdf.return_value = PDF_OK
        out_fn = "output"
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.compare_pdfs.return_value.__enter__.return_value = out_fn

        actual = compare_service.check_second_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.compare_pdfs.assert_called_with(document_id, document_id)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_fn, TaskType.compare_pdf
        )


def test_check_second_pdf_no_differences(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    with patch("pdf_bot.compare.compare_service.check_pdf") as check_pdf, patch(
        "pdf_bot.compare.compare_service.check_user_data"
    ) as _check_user_data, patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        check_pdf.return_value = PDF_OK
        telegram_context.user_data.__getitem__.return_value = document_id
        pdf_service.compare_pdfs.return_value.__enter__.side_effect = (
            NoDifferenceError()
        )

        actual = compare_service.check_second_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.compare_pdfs.assert_called_with(document_id, document_id)
        send_result_file.assert_not_called()


def test_check_second_pdf_invalid_user_data(
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

        actual = compare_service.check_second_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.compare_pdfs.assert_not_called()
        send_result_file.assert_not_called()


@pytest.mark.parametrize(
    "check_pdf_result,expected",
    [(PDF_INVALID_FORMAT, WAIT_SECOND_PDF), (PDF_TOO_LARGE, ConversationHandler.END)],
)
def test_check_second_pdf_invalid_pdf(
    compare_service: CompareService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    check_pdf_result: int,
    expected: int,
):
    with patch("pdf_bot.compare.compare_service.check_pdf") as check_pdf, patch(
        "pdf_bot.compare.compare_service.check_user_data"
    ) as _check_user_data, patch(
        "pdf_bot.compare.compare_service.send_result_file"
    ) as send_result_file:
        check_pdf.return_value = check_pdf_result

        actual = compare_service.check_second_pdf(telegram_update, telegram_context)

        assert actual == expected
        pdf_service.compare_pdfs.assert_not_called()
        send_result_file.assert_not_called()
