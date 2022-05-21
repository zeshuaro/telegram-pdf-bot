# pylint: disable=no-member

import os

from dependency_injector import containers, providers
from dotenv import load_dotenv
from telegram.ext import Updater

from pdf_bot.account import AccountRepository, AccountService
from pdf_bot.command import CommandService
from pdf_bot.compare import CompareHandlers, CompareService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService
from pdf_bot.watermark import WatermarkHandlers, WatermarkService

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TIMEOUT = 45


class Core(containers.DeclarativeContainer):
    updater = providers.Resource(
        Updater,
        token=TELEGRAM_TOKEN,
        request_kwargs={"connect_timeout": TIMEOUT, "read_timeout": TIMEOUT},
        workers=8,
    )


class Repositories(containers.DeclarativeContainer):
    account = providers.Singleton(AccountRepository)


class Services(containers.DeclarativeContainer):
    core = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    account = providers.Factory(AccountService, account_repository=repositories.account)
    command = providers.Factory(CommandService, account_service=account)
    telegram = providers.Factory(TelegramService, updater=core.updater)
    pdf = providers.Factory(PdfService, telegram_service=telegram)
    compare = providers.Factory(CompareService, pdf_service=pdf)
    watermark = providers.Factory(WatermarkService, pdf_service=pdf)


class Handlers(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()

    compare = providers.Factory(CompareHandlers, compare_service=services.compare)
    watermark = providers.Factory(
        WatermarkHandlers, watermark_service=services.watermark
    )


class Application(containers.DeclarativeContainer):
    core = providers.Container(Core)
    repositories = providers.Container(Repositories)
    services = providers.Container(Services, core=core, repositories=repositories)
    handlers = providers.Container(Handlers, services=services)
