from pdf_bot.file_processor import AbstractFileTaskProcessor

from .abstract_image_processor import AbstractImageProcessor


class ImageTaskProcessor(AbstractFileTaskProcessor):
    @property
    def processor_type(self) -> type[AbstractImageProcessor]:
        return AbstractImageProcessor
