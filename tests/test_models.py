from unittest.mock import MagicMock

import pytest

from pdf_bot.models import FileData, TaskData
from tests.telegram_internal import TelegramTestMixin


class UnknownTelegramObject:
    pass


class TestFileData(TelegramTestMixin):
    def test_from_telegram_document(self) -> None:
        actual = FileData.from_telegram_object(self.telegram_document)
        assert actual == FileData(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME
        )

    def test_from_telegram_photo_size(self) -> None:
        actual = FileData.from_telegram_object(self.telegram_photo_size)
        assert actual == FileData(self.TELEGRAM_PHOTO_SIZE_ID)

    def test_from_unknown_telegram_object(self) -> None:
        with pytest.raises(ValueError):
            FileData.from_telegram_object(UnknownTelegramObject())  # type: ignore


class TestTaskData(TelegramTestMixin):
    def test_get_file_data(self) -> None:
        expected = MagicMock()
        mock_data_type = MagicMock(spec=FileData)
        mock_data_type.from_telegram_object.return_value = expected
        sut = TaskData("label", mock_data_type)

        actual = sut.get_file_data(self.telegram_document)

        assert actual == expected
        mock_data_type.from_telegram_object.assert_called_once_with(
            self.telegram_document
        )
