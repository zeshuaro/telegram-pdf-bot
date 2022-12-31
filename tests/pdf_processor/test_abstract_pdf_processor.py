from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from telegram.ext import BaseHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.pdf_processor import AbstractPdfProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin


class MockProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return MagicMock(spec=TaskType)

    @property
    def task_data(self) -> TaskData:
        return MagicMock(spec=TaskData)

    @property
    def handler(self) -> BaseHandler:
        return MagicMock(spec=BaseHandler)

    @asynccontextmanager
    async def process_file_task(self, _file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        yield MagicMock(spec=FileTaskResult)


class TestAbstractPdfProcessor(LanguageServiceTestMixin, TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.pdf_processors_patcher = patch(
            "pdf_bot.pdf_processor.abstract_pdf_processor.AbstractPdfProcessor._PDF_PROCESSORS"
        )
        self.file_processor_patcher = patch(
            "pdf_bot.pdf_processor.abstract_pdf_processor.AbstractFileProcessor.__init__"
        )

        self.pdf_processors = self.pdf_processors_patcher.start()
        self.file_processor_patcher.start()

    def teardown_method(self) -> None:
        self.pdf_processors_patcher.stop()
        self.file_processor_patcher.stop()
        super().teardown_method()

    def test_init(self) -> None:
        processors: dict = {}
        self.pdf_processors.__contains__.side_effect = processors.__contains__

        proc = MockProcessor(self.pdf_service, self.telegram_service, self.language_service)

        self.pdf_processors.__setitem__.assert_called_once_with(proc.__class__.__name__, proc)

    def test_init_already_initialized(self) -> None:
        processors: dict = {MockProcessor.__name__: MagicMock()}
        with pytest.raises(ValueError):
            self.pdf_processors.__contains__.side_effect = processors.__contains__
            MockProcessor(self.pdf_service, self.telegram_service, self.language_service)

        self.pdf_processors.__setitem__.assert_not_called()

    def test_get_task_data_list(self) -> None:
        task_data = MagicMock(spec=TaskData)
        processor = MagicMock(spec=AbstractPdfProcessor)
        processor.task_data = task_data
        self.pdf_processors.values.return_value = [processor]

        actual = AbstractPdfProcessor.get_task_data_list()

        assert actual == [task_data]

    def test_generic_error_types(self) -> None:
        processor = MockProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )
        assert processor.generic_error_types == {PdfServiceError}
