from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.file_task import FileTaskService
from pdf_bot.image import ImageService
from pdf_bot.language_new import LanguageService
from pdf_bot.telegram_internal import TelegramService


class AbstractImageProcessor(AbstractFileProcessor):
    def __init__(
        self,
        file_task_service: FileTaskService,
        image_service: ImageService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.image_service = image_service
        super().__init__(file_task_service, telegram_service, language_service)
