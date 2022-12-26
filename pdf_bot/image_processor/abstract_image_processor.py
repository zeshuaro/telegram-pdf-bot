from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.file_task import FileTaskService
from pdf_bot.image import ImageService
from pdf_bot.language import LanguageService
from pdf_bot.telegram_internal import TelegramService


class AbstractImageProcessor(AbstractFileProcessor):
    _IMAGE_PROCESSORS: dict[str, "AbstractImageProcessor"] = {}

    def __init__(
        self,
        file_task_service: FileTaskService,
        image_service: ImageService,
        telegram_service: TelegramService,
        language_service: LanguageService,
        bypass_init_check: bool = False,
    ) -> None:
        self.image_service = image_service
        cls_name = self.__class__.__name__

        if not bypass_init_check and cls_name in self._IMAGE_PROCESSORS:
            raise ValueError(f"Class has already been initialised: {cls_name}")
        self._IMAGE_PROCESSORS[cls_name] = self

        super().__init__(
            file_task_service, telegram_service, language_service, bypass_init_check
        )

    @classmethod
    def get_processors(cls) -> list["AbstractImageProcessor"]:
        return list(cls._IMAGE_PROCESSORS.values())
