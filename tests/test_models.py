import pytest

from pdf_bot.models import FileData
from tests.telegram_internal import TelegramTestMixin


class UnknownTelegramObject:
    pass


class TestFileData(TelegramTestMixin):
    def test_from_telegram_document(self) -> None:
        actual = FileData.from_telegram_object(self.telegram_document)

        assert actual == FileData(
            self.telegram_document_id, self.telegram_document_name
        )

    def test_from_telegram_photo_size(self) -> None:
        actual = FileData.from_telegram_object(self.telegram_photo_size)

        assert actual == FileData(self.telegram_photo_size_id)

    def test_from_unknown_telegram_object(self) -> None:
        with pytest.raises(ValueError):
            FileData.from_telegram_object(UnknownTelegramObject())
