# # pylint: disable=no-member

# from unittest.mock import MagicMock

# from dependency_injector.providers import Container, Singleton
# from telegram.ext import Application as TelegramApp

# from pdf_bot.containers import Application


# class TestContainer:
#     def test_container(self) -> None:
#         telegram_app = MagicMock(spec=TelegramApp)
#         app = Application()

#         with app.core.telegram_app.override(telegram_app):
#             self._test_providers(app.repositories)
#             self._test_providers(app.services)
#             self._test_providers(app.processors)
#             self._test_providers(app.handlers)

#     def _test_providers(self, container: Container) -> None:
#         for provider in container.providers.values():  # type: ignore
#             if isinstance(provider, Singleton):
#                 provided = provider()
#                 assert isinstance(provided, provider.cls)
