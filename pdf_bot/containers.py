# pylint: disable=no-member

import os

from dependency_injector import containers, providers
from dotenv import load_dotenv
from telegram.ext import Updater

from pdf_bot.account import AccountRepository, AccountService
from pdf_bot.cli import CLIService
from pdf_bot.command import CommandService
from pdf_bot.compare import CompareHandlers, CompareService
from pdf_bot.crop import CropService
from pdf_bot.decrypt import DecryptService
from pdf_bot.encrypt import EncryptService
from pdf_bot.file import FileHandlers, FileService
from pdf_bot.file_task import FileTaskService
from pdf_bot.io import IOService
from pdf_bot.language_new import LanguageRepository, LanguageService
from pdf_bot.merge import MergeHandlers, MergeService
from pdf_bot.pdf import PdfService
from pdf_bot.rename import RenameService
from pdf_bot.rotate import RotateService
from pdf_bot.scale import ScaleService
from pdf_bot.split import SplitService
from pdf_bot.telegram import TelegramService
from pdf_bot.text import TextHandlers, TextRepository, TextService
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
    language = providers.Singleton(LanguageRepository)
    text = providers.Singleton(TextRepository)


class Services(containers.DeclarativeContainer):
    core = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    cli = providers.Factory(CLIService)
    io = providers.Factory(IOService)
    file_task = providers.Factory(FileTaskService)

    account = providers.Factory(AccountService, account_repository=repositories.account)
    command = providers.Factory(CommandService, account_service=account)
    language = providers.Factory(
        LanguageService, language_repository=repositories.language
    )
    telegram = providers.Factory(
        TelegramService, io_service=io, language_service=language, updater=core.updater
    )
    pdf = providers.Factory(
        PdfService, cli_service=cli, io_service=io, telegram_service=telegram
    )

    compare = providers.Factory(
        CompareService,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    file = providers.Factory(FileService, pdf_service=pdf, telegram_service=telegram)
    crop = providers.Factory(
        CropService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    decrypt = providers.Factory(
        DecryptService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    encrypt = providers.Factory(
        EncryptService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    language = providers.Factory(
        LanguageService, language_repository=repositories.language
    )
    merge = providers.Factory(MergeService, pdf_service=pdf, telegram_service=telegram)
    rename = providers.Factory(
        RenameService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    rotate = providers.Factory(
        RotateService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    scale = providers.Factory(
        ScaleService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    split = providers.Factory(
        SplitService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    text = providers.Factory(
        TextService,
        text_repository=repositories.text,
        pdf_service=pdf,
        telegram_service=telegram,
    )
    watermark = providers.Factory(
        WatermarkService, pdf_service=pdf, telegram_service=telegram
    )


class Handlers(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()

    compare = providers.Factory(CompareHandlers, compare_service=services.compare)
    file = providers.Factory(
        FileHandlers,
        file_task_service=services.file_task,
        file_service=services.file,
        crop_service=services.crop,
        decrypt_service=services.decrypt,
        encrypt_service=services.encrypt,
        rename_service=services.rename,
        rotate_service=services.rotate,
        scale_service=services.scale,
        split_service=services.split,
    )
    merge = providers.Factory(MergeHandlers, merge_service=services.merge)
    text = providers.Factory(TextHandlers, text_service=services.text)
    watermark = providers.Factory(
        WatermarkHandlers, watermark_service=services.watermark
    )


class Application(containers.DeclarativeContainer):
    core = providers.Container(Core)
    repositories = providers.Container(Repositories)
    services = providers.Container(Services, core=core, repositories=repositories)
    handlers = providers.Container(Handlers, services=services)
