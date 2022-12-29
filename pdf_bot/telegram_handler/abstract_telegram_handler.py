from abc import ABC, abstractmethod

from telegram.ext import BaseHandler


class AbstractTelegramHandler(ABC):
    @property
    @abstractmethod
    def handlers(self) -> list[BaseHandler]:
        pass
