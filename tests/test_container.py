# pylint: disable=no-member


from unittest.mock import MagicMock

from dependency_injector.providers import Container, Singleton
from google.cloud.datastore import Client as DatastoreClient

from pdf_bot.containers import Application


class TestContainer:
    def test_container(self) -> None:
        app = Application()
        datastore = MagicMock(spec=DatastoreClient)

        with app.clients.datastore.override(datastore):
            self._test_providers(app.repositories)
            self._test_providers(app.services)
            self._test_providers(app.processors)
            self._test_providers(app.handlers)

    def _test_providers(self, container: Container) -> None:
        for provider in container.providers.values():  # type: ignore
            if isinstance(provider, Singleton):
                provided = provider()
                assert isinstance(provided, provider.cls)
