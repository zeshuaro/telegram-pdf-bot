from random import randint
from typing import Callable, List
from unittest.mock import MagicMock, call

import pytest
from telegram import Bot, Document, File, Message
from telegram.constants import MAX_FILESIZE_DOWNLOAD

from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.telegram import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramService,
)


@pytest.fixture(name="telegram_service")
def fixture_telegram_service(
    io_service: IOService, telegram_bot: Bot
) -> TelegramService:
    return TelegramService(io_service, bot=telegram_bot)


def test_check_pdf_document(
    telegram_service: TelegramService,
    telegram_message: Message,
    telegram_document: Document,
):
    telegram_document.mime_type = "pdf"
    telegram_document.file_size = MAX_FILESIZE_DOWNLOAD
    telegram_message.document = telegram_document

    actual = telegram_service.check_pdf_document(telegram_message)

    assert actual == telegram_document


def test_check_pdf_document_invalid_mime_type(
    telegram_service: TelegramService,
    telegram_message: Message,
    telegram_document: Document,
):
    telegram_document.mime_type = "clearly_random"
    telegram_message.document = telegram_document

    with pytest.raises(TelegramFileMimeTypeError):
        telegram_service.check_pdf_document(telegram_message)


def test_check_pdf_document_too_large(
    telegram_service: TelegramService,
    telegram_message: Message,
    telegram_document: Document,
):
    telegram_document.mime_type = "pdf"
    telegram_document.file_size = MAX_FILESIZE_DOWNLOAD + 1
    telegram_message.document = telegram_document

    with pytest.raises(TelegramFileTooLargeError):
        telegram_service.check_pdf_document(telegram_message)


def test_download_file(
    telegram_service: TelegramService,
    telegram_bot: Bot,
    telegram_file: File,
    document_id: str,
):
    telegram_bot.get_file.return_value = telegram_file
    with telegram_service.download_file(document_id):
        telegram_bot.get_file.assert_called_with(document_id)
        telegram_file.download.assert_called()


def test_download_files(
    telegram_service: TelegramService,
    telegram_bot: Bot,
    document_ids_generator: Callable[[int], List[str]],
):
    def get_file_side_effect(doc_id: str):
        mock = MagicMock()
        mock.__enter__.return_value = File(doc_id, doc_id)
        return mock

    num_files = randint(2, 10)
    file_ids = document_ids_generator(num_files)
    telegram_bot.get_file.side_effect = get_file_side_effect

    with telegram_service.download_files(file_ids):
        calls = [call(file_id) for file_id in file_ids]
        telegram_bot.get_file.assert_has_calls(calls)


def test_send_file_names(telegram_service: TelegramService, telegram_bot: Bot):
    chat_id = "chat_id"
    text = "text"
    file_data_list = [FileData("a", "a"), FileData("b", "b")]

    telegram_service.send_file_names(chat_id, text, file_data_list)

    telegram_bot.send_message.assert_called_once_with(chat_id, f"{text}1: a\n2: b\n")
