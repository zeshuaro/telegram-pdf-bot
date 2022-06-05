from random import randint
from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.crop import CropService, crop_constants
from pdf_bot.file_task import FileTaskService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramUserDataKeyError


@pytest.fixture(name="crop_service")
def fixture_crop_service(
    file_task_service: FileTaskService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
) -> CropService:
    return CropService(file_task_service, pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.crop.crop_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_crop_type(
    crop_service: CropService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = crop_service.ask_crop_type(telegram_update, telegram_context)
    assert actual == crop_constants.WAIT_CROP_TYPE


def test_crop_pdf_by_percentage(
    crop_service: CropService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    percent = float(
        randint(crop_constants.MIN_PERCENTAGE, crop_constants.MAX_PERCENTAGE)
    )

    telegram_message.text = percent
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.crop_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.crop.crop_service.send_result_file") as send_result_file:
        actual = crop_service.crop_pdf_by_percentage(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.crop_pdf.assert_called_once_with(
            file_id, percentage=percent, margin_size=None
        )
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.crop_pdf
        )


def test_crop_pdf_by_percentage_invalid_user_data(
    crop_service: CropService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    percent = float(
        randint(crop_constants.MIN_PERCENTAGE, crop_constants.MAX_PERCENTAGE)
    )

    telegram_message.text = percent
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

    with patch("pdf_bot.crop.crop_service.send_result_file") as send_result_file:
        actual = crop_service.crop_pdf_by_percentage(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.crop_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_crop_pdf_by_percentage_invalid_value(
    crop_service: CropService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    percent = "clearly_invalid"

    telegram_message.text = percent
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.crop_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.crop.crop_service.send_result_file") as send_result_file:
        actual = crop_service.crop_pdf_by_percentage(telegram_update, telegram_context)

        assert actual == crop_constants.WAIT_CROP_PERCENTAGE
        telegram_service.get_user_data.assert_not_called()
        pdf_service.crop_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_crop_pdf_by_margin_size(
    crop_service: CropService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    margin_size = float(randint(1, 10))

    telegram_message.text = margin_size
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.crop_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.crop.crop_service.send_result_file") as send_result_file:
        actual = crop_service.crop_pdf_by_margin_size(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.crop_pdf.assert_called_once_with(
            file_id, percentage=None, margin_size=margin_size
        )
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.crop_pdf
        )


def test_crop_pdf_by_margin_size_invalid_user_data(
    crop_service: CropService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    margin_size = float(randint(1, 10))

    telegram_message.text = margin_size
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

    with patch("pdf_bot.crop.crop_service.send_result_file") as send_result_file:
        actual = crop_service.crop_pdf_by_margin_size(telegram_update, telegram_context)

        assert actual == ConversationHandler.END
        telegram_service.get_user_data.assert_called_once_with(
            telegram_context, PDF_INFO
        )
        pdf_service.crop_pdf.assert_not_called()
        send_result_file.assert_not_called()


def test_crop_pdf_by_margin_size_invalid_value(
    crop_service: CropService,
    pdf_service: PdfService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_message: Message,
):
    file_id = "file_id"
    out_path = "out_path"
    margin_size = "clearly_invalid"

    telegram_message.text = margin_size
    telegram_update.effective_message = telegram_message

    telegram_service.get_user_data.return_value = (file_id, "file_name")
    pdf_service.crop_pdf.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.crop.crop_service.send_result_file") as send_result_file:
        actual = crop_service.crop_pdf_by_margin_size(telegram_update, telegram_context)

        assert actual == crop_constants.WAIT_CROP_MARGIN_SIZE
        telegram_service.get_user_data.assert_not_called()
        pdf_service.crop_pdf.assert_not_called()
        send_result_file.assert_not_called()
