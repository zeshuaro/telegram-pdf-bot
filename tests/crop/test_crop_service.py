from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.crop import CropService
from pdf_bot.file_task import FileTaskService
from pdf_bot.language_new import LanguageService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramUserDataKeyError
from tests.telegram.telegram_test_mixin import TelegramTestMixin


class TestCropService(TelegramTestMixin):
    WAIT_CROP_TYPE = "wait_crop_type"
    WAIT_CROP_PERCENTAGE = "wait_crop_percentage"
    WAIT_CROP_MARGIN_SIZE = "wait_crop_margin_size"
    WAIT_PDF_TASK = "wait_pdf_task"

    BY_PERCENTAGE = "By percentage"
    BY_MARGIN_SIZE = "By margin size"
    BACK = "Back"

    PERCENT = 0.1
    MARGIN_SIZE = 10
    FILE_PATH = "file_path"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)

        self.file_task_service = MagicMock(spec=FileTaskService)
        self.file_task_service.ask_pdf_task.return_value = self.WAIT_PDF_TASK

        self.language_service = MagicMock(spec=LanguageService)
        self.language_service.set_app_language.return_value = lambda x: x

        self.telegram_service = MagicMock(spec=TelegramService)
        self.telegram_service.check_pdf_document.return_value = self.telegram_document

        self.sut = CropService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_ask_crop_type(self) -> None:
        actual = self.sut.ask_crop_type(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_CROP_TYPE
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.parametrize(
        "text,expected",
        [
            (BY_PERCENTAGE, WAIT_CROP_PERCENTAGE),
            (BY_MARGIN_SIZE, WAIT_CROP_MARGIN_SIZE),
            (BACK, WAIT_PDF_TASK),
            ("clearly_invalid", WAIT_CROP_TYPE),
        ],
    )
    def test_check_crop_type(self, text: str, expected: str) -> None:
        self.telegram_message.text = text
        actual = self.sut.check_crop_type(self.telegram_update, self.telegram_context)
        assert actual == expected

    def test_crop_pdf_by_percentage(self) -> None:
        self.telegram_message.text = self.PERCENT
        self.telegram_service.get_user_data.return_value = (
            self.telegram_document_id,
            "file_name",
        )
        self.pdf_service.crop_pdf.return_value.__enter__.return_value = self.FILE_PATH

        actual = self.sut.crop_pdf_by_percentage(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_crop_success(percentage=self.PERCENT)

    def test_crop_pdf_by_percentage_invalid_user_data(self) -> None:
        self.telegram_message.text = self.PERCENT
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = self.sut.crop_pdf_by_percentage(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_crop_invalid_user_data()

    def test_crop_pdf_by_percentage_invalid_value(self) -> None:
        self.telegram_message.text = "clearly_invalid"

        actual = self.sut.crop_pdf_by_percentage(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_CROP_PERCENTAGE
        self._assert_crop_invalid_value()

    def test_crop_pdf_by_margin_size(self) -> None:
        self.telegram_message.text = self.MARGIN_SIZE
        self.telegram_service.get_user_data.return_value = (
            self.telegram_document_id,
            "file_name",
        )
        self.pdf_service.crop_pdf.return_value.__enter__.return_value = self.FILE_PATH

        actual = self.sut.crop_pdf_by_margin_size(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_crop_success(margin_size=self.MARGIN_SIZE)

    def test_crop_pdf_by_margin_size_invalid_user_data(self) -> None:
        self.telegram_message.text = self.MARGIN_SIZE
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = self.sut.crop_pdf_by_margin_size(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_crop_invalid_user_data()

    def test_crop_pdf_by_margin_size_invalid_value(self) -> None:
        self.telegram_message.text = "clearly_invalid"

        actual = self.sut.crop_pdf_by_margin_size(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_CROP_MARGIN_SIZE
        self._assert_crop_invalid_value()

    def _assert_crop_success(
        self, percentage: float | None = None, margin_size: int | None = None
    ) -> None:
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.pdf_service.crop_pdf.assert_called_once_with(
            self.telegram_document_id, percentage=percentage, margin_size=margin_size
        )
        self.telegram_service.reply_with_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.crop_pdf,
        )

    def _assert_crop_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.pdf_service.crop_pdf.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()

    def _assert_crop_invalid_value(self) -> None:
        self.telegram_service.get_user_data.assert_not_called()
        self.pdf_service.crop_pdf.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()
