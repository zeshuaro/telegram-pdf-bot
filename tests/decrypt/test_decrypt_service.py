from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.decrypt import DecryptService, decrypt_constants
from pdf_bot.file_task import FileTaskService
from pdf_bot.pdf import PdfIncorrectPasswordError, PdfService
from pdf_bot.telegram import TelegramService, TelegramUserDataKeyError


@pytest.fixture(name="decrypt_service")
def fixture_decrypt_service(
    file_task_service: FileTaskService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
) -> DecryptService:
    return DecryptService(file_task_service, pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.decrypt.decrypt_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def files_set_lang() -> Iterator[None]:
    with patch("pdf_bot.files.utils.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_password(
    decrypt_service: DecryptService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = decrypt_service.ask_password(telegram_update, telegram_context)
    assert actual == decrypt_constants.WAIT_DECRYPT_PASSWORD


def test_decrypt_pdf(
    decrypt_service: DecryptService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_text: str,
):
    file_id = "file_id"
    out_path = "out_path"

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.decrypt_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.decrypt.decrypt_service.send_result_file") as send_result_file:
        actual = decrypt_service.decrypt_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.decrypt_pdf.assert_called_once_with(file_id, telegram_text)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.decrypt_pdf
        )


def test_decrypt_pdf_incorrect_password(
    decrypt_service: DecryptService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_text: str,
):
    file_id = "file_id"

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.decrypt_pdf.side_effect = PdfIncorrectPasswordError()

    with patch("pdf_bot.decrypt.decrypt_service.send_result_file") as send_result_file:
        actual = decrypt_service.decrypt_pdf(telegram_update, telegram_context)

        assert actual == decrypt_constants.WAIT_DECRYPT_PASSWORD
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.decrypt_pdf.assert_called_once_with(file_id, telegram_text)
        send_result_file.assert_not_called()


def test_decrypt_pdf_invalid_user_data(
    decrypt_service: DecryptService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()
    with patch("pdf_bot.decrypt.decrypt_service.send_result_file") as send_result_file:
        actual = decrypt_service.decrypt_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.decrypt_pdf.assert_not_called()
        send_result_file.assert_not_called()
