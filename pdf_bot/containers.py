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
from pdf_bot.file import FileHandlers, FileService
from pdf_bot.file_task import FileTaskService
from pdf_bot.image import ImageService
from pdf_bot.io import IOService
from pdf_bot.language_new import LanguageRepository, LanguageService
from pdf_bot.merge import MergeHandlers, MergeService
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import (
    DecryptPDFProcessor,
    EncryptPDFProcessor,
    ExtractPDFTextProcessor,
    GrayscalePDFProcessor,
    OCRPDFProcessor,
    PDFToImageProcessor,
    PreviewPDFProcessor,
    RenamePDFProcessor,
    RotatePDFProcessor,
    ScalePDFProcessor,
    SplitPDFProcessor,
)
from pdf_bot.telegram_internal import TelegramService
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

    cli = providers.Singleton(CLIService)
    io = providers.Singleton(IOService)

    account = providers.Singleton(
        AccountService, account_repository=repositories.account
    )
    language = providers.Singleton(
        LanguageService, language_repository=repositories.language
    )

    command = providers.Singleton(
        CommandService, account_service=account, language_service=language
    )
    file_task = providers.Singleton(FileTaskService, language_service=language)
    telegram = providers.Singleton(
        TelegramService, io_service=io, language_service=language, updater=core.updater
    )

    image = providers.Singleton(
        ImageService, cli_service=cli, io_service=io, telegram_service=telegram
    )
    pdf = providers.Singleton(
        PdfService, cli_service=cli, io_service=io, telegram_service=telegram
    )

    compare = providers.Singleton(
        CompareService,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    file = providers.Singleton(
        FileService,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    crop = providers.Singleton(
        CropService,
        file_task_service=file_task,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    language = providers.Singleton(
        LanguageService, language_repository=repositories.language
    )
    merge = providers.Singleton(
        MergeService,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    text = providers.Singleton(
        TextService,
        text_repository=repositories.text,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    watermark = providers.Singleton(
        WatermarkService,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )


class Processors(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()

    decrypt = providers.Singleton(
        DecryptPDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    encrypt = providers.Singleton(
        EncryptPDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    extract_text = providers.Singleton(
        ExtractPDFTextProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    grayscale = providers.Singleton(
        GrayscalePDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    ocr = providers.Singleton(
        OCRPDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    pdf_to_image = providers.Singleton(
        PDFToImageProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    preview_pdf = providers.Singleton(
        PreviewPDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    rename = providers.Singleton(
        RenamePDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    rotate = providers.Singleton(
        RotatePDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    scale = providers.Singleton(
        ScalePDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    split = providers.Singleton(
        SplitPDFProcessor,
        file_task_service=services.file_task,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )


class Handlers(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()
    processors = providers.DependenciesContainer()

    compare = providers.Singleton(CompareHandlers, compare_service=services.compare)
    file = providers.Singleton(
        FileHandlers,
        file_task_service=services.file_task,
        file_service=services.file,
        crop_service=services.crop,
        decrypt_pdf_processor=processors.decrypt,
        encrypt_pdf_processor=processors.encrypt,
        extract_pdf_text_processor=processors.extract_text,
        grayscale_pdf_processor=processors.grayscale,
        ocr_pdf_processor=processors.ocr,
        pdf_to_image_processor=processors.pdf_to_image,
        preview_pdf_processor=processors.preview_pdf,
        rename_pdf_processor=processors.rename,
        rotate_pdf_processor=processors.rotate,
        scale_pdf_processor=processors.scale,
        split_pdf_processor=processors.split,
    )
    merge = providers.Singleton(MergeHandlers, merge_service=services.merge)
    text = providers.Singleton(TextHandlers, text_service=services.text)
    watermark = providers.Singleton(
        WatermarkHandlers, watermark_service=services.watermark
    )


class Application(containers.DeclarativeContainer):
    core = providers.Container(Core)
    repositories = providers.Container(Repositories)
    services = providers.Container(Services, core=core, repositories=repositories)
    processors = providers.Container(Processors, services=services)
    handlers = providers.Container(Handlers, services=services, processors=processors)
