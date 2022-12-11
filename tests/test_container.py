# pylint: disable=no-member

from unittest.mock import MagicMock

from dependency_injector.providers import Container, Singleton
from telegram.ext import Updater

from pdf_bot.containers import Application


class TestContainer:
    def test_container(self) -> None:
        updater = MagicMock(spec=Updater)
        app = Application()

        with app.core.updater.override(updater):
            self._test_providers(app.repositories)
            self._test_providers(app.services)
            self._test_providers(app.processors)
            self._test_providers(app.handlers)

    def _test_providers(self, container: Container) -> None:
        for provider in container.providers.values():
            if isinstance(provider, Singleton):
                provided = provider()
                assert isinstance(provided, provider.cls)
