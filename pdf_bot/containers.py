from dependency_injector import containers, providers

from pdf_bot.account import AccountRepository, AccountService
from pdf_bot.command import CommandService


class Core(containers.DeclarativeContainer):
    pass


class Repositories(containers.DeclarativeContainer):
    account = providers.Singleton(AccountRepository)


class Services(containers.DeclarativeContainer):
    repositories = providers.DependenciesContainer()

    account = providers.Factory(
        AccountService,
        account_repository=repositories.account,  # pylint: disable=no-member
    )
    command = providers.Factory(CommandService, account_service=account)


class Application(containers.DeclarativeContainer):
    core = providers.Container(Core)
    repositories = providers.Container(Repositories)
    services = providers.Container(Services, repositories=repositories)
