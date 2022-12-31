from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.language import LanguageService
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramService


class AbstractPdfProcessor(AbstractFileProcessor):
    _PDF_PROCESSORS: dict[str, "AbstractPdfProcessor"] = {}

    def __init__(
        self,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
        bypass_init_check: bool = False,
    ) -> None:
        super().__init__(telegram_service, language_service, bypass_init_check)

        self.pdf_service = pdf_service
        cls_name = self.__class__.__name__

        if not bypass_init_check and cls_name in self._PDF_PROCESSORS:
            raise ValueError(f"Class has already been initialised: {cls_name}")
        self._PDF_PROCESSORS[cls_name] = self

    @classmethod
    def get_task_data_list(cls) -> list[TaskData]:
        return [x.task_data for x in cls._PDF_PROCESSORS.values()]

    @property
    def generic_error_types(self) -> set[type[Exception]]:
        return {PdfServiceError}
