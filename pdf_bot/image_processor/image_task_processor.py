from typing import Type

from pdf_bot.file_processor import AbstractFileTaskProcessor

from .abstract_image_processor import AbstractImageProcessor


class ImageTaskProcessor(AbstractFileTaskProcessor):
    @property
    def processor_type(self) -> Type[AbstractImageProcessor]:
        return AbstractImageProcessor
