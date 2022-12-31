from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import CropOptionAndInputData, CropPdfData, CropPdfProcessor, CropType
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestPdfProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):

    CROP_TEXT = "0.1"
    CROP_VALUE = float(CROP_TEXT)

    def setup_method(self) -> None:
        super().setup_method()
        self.crop_pdf_data = CropPdfData(self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME)

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = CropPdfProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_entry_point_data_type(self) -> None:
        actual = self.sut.entry_point_data_type
        assert actual == CropPdfData

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.crop_pdf

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Crop", CropPdfData)

    def test_select_option_type(self) -> None:
        actual = self.sut.select_option_type
        assert actual == CropType

    def test_option_and_input_data_type(self) -> None:
        actual = self.sut.option_and_input_data_type
        assert actual == CropOptionAndInputData

    def test_get_cleaned_text_input(self) -> None:
        actual = self.sut.get_cleaned_text_input(self.CROP_TEXT)
        assert actual == self.CROP_VALUE

    def test_get_cleaned_text_input_invalid(self) -> None:
        actual = self.sut.get_cleaned_text_input("clearly_invalid")
        assert actual is None

    @pytest.mark.asyncio
    async def test_process_file_task_scale_by_factor(self) -> None:
        file_data = CropOptionAndInputData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            option=CropType.by_percentage,
            text=self.CROP_VALUE,
        )
        self.pdf_service.crop_pdf_by_percentage.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
            file_data
        ) as actual:
            assert actual == self.FILE_TASK_RESULT
            self.pdf_service.crop_pdf_by_percentage.assert_called_once_with(
                file_data.id, self.CROP_VALUE
            )

    @pytest.mark.asyncio
    async def test_process_file_task_scale_to_dimension(self) -> None:
        file_data = CropOptionAndInputData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            option=CropType.by_margin_size,
            text=self.CROP_VALUE,
        )
        self.pdf_service.crop_pdf_by_margin_size.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
            file_data
        ) as actual:
            assert actual == self.FILE_TASK_RESULT
            self.pdf_service.crop_pdf_by_margin_size.assert_called_once_with(
                file_data.id, self.CROP_VALUE
            )

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_scale_type(self) -> None:
        file_data = CropOptionAndInputData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            option=None,  # type: ignore
            text=self.CROP_VALUE,
        )

        with pytest.raises(ValueError):
            async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
                file_data
            ):
                self.pdf_service.crop_pdf_by_percentage.assert_not_called()
                self.pdf_service.crop_pdf_by_margin_size.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
                self.FILE_DATA
            ):
                self.pdf_service.crop_pdf_by_percentage.assert_not_called()
                self.pdf_service.crop_pdf_by_margin_size.assert_not_called()
