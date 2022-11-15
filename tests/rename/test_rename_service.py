from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.pdf import PdfService
from pdf_bot.rename import RenameService, rename_constants
from pdf_bot.telegram_internal import TelegramService, TelegramUserDataKeyError


@pytest.fixture(name="rename_service")
def fixture_rename_service(
    file_task_service: FileTaskService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
) -> RenameService:
    return RenameService(file_task_service, pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.rename.rename_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def files_set_lang() -> Iterator[None]:
    with patch("pdf_bot.files.utils.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_new_file_name(
    rename_service: RenameService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = rename_service.ask_new_file_name(telegram_update, telegram_context)
    assert actual == rename_constants.WAIT_NEW_FILE_NAME


def test_rename_pdf(
    rename_service: RenameService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_text: str,
):
    file_id = "file_id"
    out_path = "out_path"

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.rename_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.rename.rename_service.send_result_file") as send_result_file:
        actual = rename_service.rename_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.rename_pdf.assert_called_once_with(file_id, f"{telegram_text}.pdf")
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.rename_pdf
        )


def test_rename_pdf_invalid_user_data(
    rename_service: RenameService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()
    with patch("pdf_bot.rename.rename_service.send_result_file") as send_result_file:
        actual = rename_service.rename_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.rename_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_rename_pdf_invalid_file_name(
    rename_service: RenameService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    telegram_message.text = "invalid/file?name"
    telegram_update.effective_message = telegram_message

    with patch("pdf_bot.rename.rename_service.send_result_file") as send_result_file:
        actual = rename_service.rename_pdf(telegram_update, telegram_context)

        assert actual == rename_constants.WAIT_NEW_FILE_NAME
        telegram_service.get_user_data.assert_not_called()
        pdf_service.rename_pdf.assert_not_called()
        send_result_file.assert_not_called()
