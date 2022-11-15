from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.pdf import PdfService
from pdf_bot.rotate import RotateService, rotate_constants
from pdf_bot.telegram_internal import TelegramService, TelegramUserDataKeyError


@pytest.fixture(name="rotate_service")
def fixture_rotate_service(
    file_task_service: FileTaskService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
) -> RotateService:
    return RotateService(file_task_service, pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.rotate.rotate_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def files_set_lang() -> Iterator[None]:
    with patch("pdf_bot.files.utils.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_degree(
    rotate_service: RotateService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = rotate_service.ask_degree(telegram_update, telegram_context)
    assert actual == rotate_constants.WAIT_ROTATE_DEGREE


def test_rotate_pdf(
    rotate_service: RotateService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    degree = "90"

    telegram_message.text = degree
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.rotate_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.rotate.rotate_service.send_result_file") as send_result_file:
        actual = rotate_service.rotate_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.rotate_pdf.assert_called_once_with(file_id, int(degree))
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.rotate_pdf
        )


def test_rotate_pdf_invalid_user_data(
    rotate_service: RotateService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    telegram_message.text = "90"
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

    with patch("pdf_bot.rotate.rotate_service.send_result_file") as send_result_file:
        actual = rotate_service.rotate_pdf(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.rotate_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_rotate_pdf_invalid_degree(
    rotate_service: RotateService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    telegram_message.text = "clearly_invalid_degree"
    telegram_update.effective_message = telegram_message

    with patch("pdf_bot.rotate.rotate_service.send_result_file") as send_result_file:
        actual = rotate_service.rotate_pdf(telegram_update, telegram_context)

        assert actual is None
        telegram_service.get_user_data.assert_not_called()
        pdf_service.rotate_pdf.assert_not_called()
        send_result_file.assert_not_called()
