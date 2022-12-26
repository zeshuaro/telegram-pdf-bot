# pylint: disable=no-member


from dependency_injector.providers import Container, Singleton

from pdf_bot.containers import Application


class TestContainer:
    def test_container(self) -> None:
        app = Application()

        self._test_providers(app.repositories)
        self._test_providers(app.services)
        self._test_providers(app.processors)
        self._test_providers(app.handlers)

    def _test_providers(self, container: Container) -> None:
        for provider in container.providers.values():  # type: ignore
            if isinstance(provider, Singleton):
                provided = provider()
                assert isinstance(provided, provider.cls)
