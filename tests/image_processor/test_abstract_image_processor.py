from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from telegram.ext import BaseHandler

from pdf_bot.analytics import TaskType
from pdf_bot.image import ImageService
from pdf_bot.image_processor import AbstractImageProcessor
from pdf_bot.models import FileData, FileTaskResult, TaskData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin


class MockProcessor(AbstractImageProcessor):
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


class TestAbstractImageProcessor(LanguageServiceTestMixin, TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.image_service = MagicMock(spec=ImageService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.image_processors_patcher = patch(
            "pdf_bot.image_processor.abstract_image_processor.AbstractImageProcessor"
            "._IMAGE_PROCESSORS"
        )
        self.file_processor_patcher = patch(
            "pdf_bot.image_processor.abstract_image_processor.AbstractFileProcessor.__init__"
        )

        self.image_processors = self.image_processors_patcher.start()
        self.file_processor_patcher.start()

    def teardown_method(self) -> None:
        self.image_processors_patcher.stop()
        self.file_processor_patcher.stop()
        super().teardown_method()

    def test_init(self) -> None:
        processors: dict = {}
        self.image_processors.__contains__.side_effect = processors.__contains__

        proc = MockProcessor(self.image_service, self.telegram_service, self.language_service)

        self.image_processors.__setitem__.assert_called_once_with(proc.__class__.__name__, proc)

    def test_init_already_initialized(self) -> None:
        processors: dict = {MockProcessor.__name__: MagicMock()}
        self.image_processors.__contains__.side_effect = processors.__contains__

        with pytest.raises(ValueError):
            MockProcessor(self.image_service, self.telegram_service, self.language_service)

        self.image_processors.__setitem__.assert_not_called()

    def test_get_task_data_list(self) -> None:
        task_data = MagicMock(spec=TaskData)
        processor = MagicMock(spec=AbstractImageProcessor)
        processor.task_data = task_data
        self.image_processors.values.return_value = [processor]

        actual = AbstractImageProcessor.get_task_data_list()

        assert actual == [task_data]
