from random import randint
from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.pdf import PdfService
from pdf_bot.pdf.models import ScaleData
from pdf_bot.scale import ScaleService, scale_constants
from pdf_bot.telegram import TelegramService, TelegramUserDataKeyError


@pytest.fixture(name="scale_service")
def fixture_scale_service(
    file_task_service: FileTaskService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
) -> ScaleService:
    return ScaleService(file_task_service, pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.scale.scale_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_scale_type(
    scale_service: ScaleService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = scale_service.ask_scale_type(telegram_update, telegram_context)
    assert actual == scale_constants.WAIT_SCALE_TYPE


def test_scale_pdf_by_factor(
    scale_service: ScaleService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    scale_data = ScaleData(randint(1, 10), randint(1, 10))

    telegram_message.text = str(scale_data)
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.scale_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.scale.scale_service.send_result_file") as send_result_file:
        actual = scale_service.scale_pdf_by_factor(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.scale_pdf.assert_called_once_with(file_id, scale_data)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.scale_pdf
        )


def test_scale_pdf_by_factor_invalid_user_data(
    scale_service: ScaleService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    scale_data = ScaleData(randint(1, 10), randint(1, 10))

    telegram_message.text = str(scale_data)
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

    with patch("pdf_bot.scale.scale_service.send_result_file") as send_result_file:
        actual = scale_service.scale_pdf_by_factor(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.scale_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_scale_pdf_by_factor_invalid_value(
    scale_service: ScaleService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"

    telegram_message.text = "clearly_invalid"
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.scale_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.scale.scale_service.send_result_file") as send_result_file:
        actual = scale_service.scale_pdf_by_factor(telegram_update, telegram_context)

        assert actual == scale_constants.WAIT_SCALE_FACTOR
        telegram_service.get_user_data.assert_not_called()
        pdf_service.scale_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_scale_pdf_to_dimension(
    scale_service: ScaleService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    scale_data = ScaleData(randint(1, 10), randint(1, 10))

    telegram_message.text = str(scale_data)
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.scale_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.scale.scale_service.send_result_file") as send_result_file:
        actual = scale_service.scale_pdf_to_dimension(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.scale_pdf.assert_called_once_with(file_id, scale_data)
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.scale_pdf
        )


def test_scale_pdf_to_dimension_invalid_user_data(
    scale_service: ScaleService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    scale_data = ScaleData(randint(1, 10), randint(1, 10))

    telegram_message.text = str(scale_data)
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

    with patch("pdf_bot.scale.scale_service.send_result_file") as send_result_file:
        actual = scale_service.scale_pdf_to_dimension(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.scale_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_scale_pdf_to_dimension_invalid_value(
    scale_service: ScaleService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"

    telegram_message.text = "clearly_invalid"
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.scale_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.scale.scale_service.send_result_file") as send_result_file:
        actual = scale_service.scale_pdf_to_dimension(telegram_update, telegram_context)

        assert actual == scale_constants.WAIT_SCALE_DIMENSION
        telegram_service.get_user_data.assert_not_called()
        pdf_service.scale_pdf.assert_not_called()
        send_result_file.assert_not_called()
