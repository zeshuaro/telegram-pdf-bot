from typing import Type
from unittest.mock import MagicMock, patch

import pytest

from pdf_bot.file_processor import AbstractFileProcessor, AbstractFileTaskProcessor
from pdf_bot.models import FileData, TaskData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class MockProcessor(AbstractFileTaskProcessor):
    TASK_DATA_LIST = [TaskData("a", FileData), TaskData("b", FileData)]

    @property
    def processor_type(self) -> Type[AbstractFileProcessor]:
        mock_type = MagicMock(spec=AbstractFileProcessor)
        mock_type.get_task_data_list.return_value = self.TASK_DATA_LIST
        return mock_type


class TestAbstractFileTaskProcessor(LanguageServiceTestMixin, TelegramTestMixin):
    WAIT_FILE_TASK = "wait_file_task"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = MockProcessor(self.language_service)

    @pytest.mark.asyncio
    async def test_ask_task(self) -> None:
        with patch.object(
            self.sut, "ask_task_helper", return_value=self.WAIT_FILE_TASK
        ) as ask_task_helper:
            actual = await self.sut.ask_task(self.telegram_update, self.telegram_context)

            assert actual == self.WAIT_FILE_TASK
            ask_task_helper.assert_called_once_with(
                self.language_service,
                self.telegram_update,
                self.telegram_context,
                MockProcessor.TASK_DATA_LIST,
            )
