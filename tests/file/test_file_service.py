from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.file import FileService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramUserDataKeyError

PDF_INFO = "pdf_info"


@pytest.fixture(name="file_service")
def fixture_file_service(
    pdf_service: PdfService, telegram_service: TelegramService
) -> FileService:
    return FileService(pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.file.file_service.set_lang"):
        yield


def test_black_and_white_pdf(
    file_service: FileService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    document_id: int,
):
    out_path = "out_path"
    telegram_service.get_user_data.return_value = document_id
    pdf_service.black_and_white_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.file.file_service.send_result_file") as send_result_file:
        actual = file_service.black_and_white_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.black_and_white_pdf.assert_called_with(document_id)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.black_and_white_pdf
        )


def test_black_and_white_pdf_invalid_user_data(
    file_service: FileService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

    with patch("pdf_bot.file.file_service.send_result_file") as send_result_file:
        actual = file_service.black_and_white_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        pdf_service.black_and_white_pdf.assert_not_called()
        send_result_file.assert_not_called()
