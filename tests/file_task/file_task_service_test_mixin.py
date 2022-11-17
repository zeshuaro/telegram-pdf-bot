from unittest.mock import MagicMock

from pdf_bot.file_task import FileTaskService


class FileTaskServiceTestMixin:
    WAIT_PDF_TASK = "wait_pdf_task"

    def mock_file_task_service(self) -> FileTaskService:
        service = MagicMock(spec=FileTaskService)
        service.ask_pdf_task.return_value = self.WAIT_PDF_TASK
        return service
