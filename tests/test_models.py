import pytest

from pdf_bot.models import FileData
from tests.telegram_internal import TelegramTestMixin


class UnknownTelegramObject:
    pass


class TestFileData(TelegramTestMixin):
    @pytest.mark.asyncio
    async def test_from_telegram_document(self) -> None:
        actual = FileData.from_telegram_object(self.telegram_document)

        assert actual == FileData(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME
        )

    @pytest.mark.asyncio
    async def test_from_telegram_photo_size(self) -> None:
        actual = FileData.from_telegram_object(self.telegram_photo_size)

        assert actual == FileData(self.TELEGRAM_PHOTO_SIZE_ID)

    @pytest.mark.asyncio
    async def test_from_unknown_telegram_object(self) -> None:
        with pytest.raises(ValueError):
            FileData.from_telegram_object(UnknownTelegramObject())  # type: ignore
