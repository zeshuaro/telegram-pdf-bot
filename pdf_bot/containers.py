# pylint: disable=no-member

import os

from dependency_injector import containers, providers
from dotenv import load_dotenv
from google.cloud.datastore import Client as DatastoreClient
from requests import Session
from slack_sdk import WebClient as SlackClient
from telegram.ext import Updater

from pdf_bot.account import AccountRepository, AccountService
from pdf_bot.analytics import AnalyticsRepository, AnalyticsService
from pdf_bot.cli import CLIService
from pdf_bot.command import CommandService
from pdf_bot.compare import CompareHandlers, CompareService
from pdf_bot.crop import CropService
from pdf_bot.feedback import FeedbackHandler, FeedbackRepository, FeedbackService
from pdf_bot.file import FileHandlers, FileService
from pdf_bot.file_task import FileTaskService
from pdf_bot.image import ImageService
from pdf_bot.image_handler import BatchImageHandler
from pdf_bot.image_processor import BeautifyImageProcessor, ImageToPDFProcessor
from pdf_bot.io import IOService
from pdf_bot.language import LanguageRepository, LanguageService
from pdf_bot.merge import MergeHandlers, MergeService
from pdf_bot.payment import PaymentService
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import (
    DecryptPDFProcessor,
    EncryptPDFProcessor,
    ExtractPDFImageProcessor,
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
from pdf_bot.telegram_dispatcher import TelegramDispatcher
from pdf_bot.telegram_internal import TelegramService
from pdf_bot.text import TextHandlers, TextRepository, TextService
from pdf_bot.watermark import WatermarkHandlers, WatermarkService
from pdf_bot.webpage import WebpageHandler, WebpageService

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
TIMEOUT = 45

GCP_KEY_FILE = os.environ.get("GCP_KEY_FILE")
GCP_CRED = os.environ.get("GCP_CRED")

if GCP_CRED is not None:
    with open(GCP_KEY_FILE, "w") as f:
        f.write(GCP_CRED)


class Core(containers.DeclarativeContainer):
    updater = providers.Resource(
        Updater,
        token=TELEGRAM_TOKEN,
        request_kwargs={"connect_timeout": TIMEOUT, "read_timeout": TIMEOUT},
        workers=8,
    )


class Clients(containers.DeclarativeContainer):
    session = Session()
    session.hooks = {"response": lambda r, *args, **kwargs: r.raise_for_status()}

    if GCP_KEY_FILE is not None:
        datastore_client = DatastoreClient.from_service_account_json(GCP_KEY_FILE)
    else:
        datastore_client = DatastoreClient()

    api = providers.Object(session)
    datastore = providers.Object(datastore_client)
    slack = providers.Object(SlackClient(SLACK_TOKEN))


class Repositories(containers.DeclarativeContainer):
    clients = providers.DependenciesContainer()

    account = providers.Singleton(AccountRepository, datastore_client=clients.datastore)
    analytics = providers.Singleton(AnalyticsRepository, api_client=clients.api)
    feedback = providers.Singleton(FeedbackRepository, slack_client=clients.slack)
    language = providers.Singleton(
        LanguageRepository, datastore_client=clients.datastore
    )
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

    analytics = providers.Singleton(
        AnalyticsService,
        analytics_repository=repositories.analytics,
        language_service=language,
    )
    command = providers.Singleton(
        CommandService, account_service=account, language_service=language
    )
    file_task = providers.Singleton(FileTaskService, language_service=language)
    telegram = providers.Singleton(
        TelegramService,
        io_service=io,
        language_service=language,
        analytics_service=analytics,
        updater=core.updater,
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
    feedback = providers.Singleton(
        FeedbackService, feedback_repository=repositories.feedback
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
    payment = providers.Singleton(
        PaymentService,
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
    webpage = providers.Singleton(WebpageService, io_service=io)


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
    extract_image = providers.Singleton(
        ExtractPDFImageProcessor,
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

    beautify = providers.Singleton(
        BeautifyImageProcessor,
        file_task_service=services.file_task,
        image_service=services.image,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    image_to_pdf = providers.Singleton(
        ImageToPDFProcessor,
        file_task_service=services.file_task,
        image_service=services.image,
        telegram_service=services.telegram,
        language_service=services.language,
    )


class Handlers(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()
    processors = providers.DependenciesContainer()

    file = providers.Singleton(
        FileHandlers,
        file_task_service=services.file_task,
        file_service=services.file,
        crop_service=services.crop,
        decrypt_pdf_processor=processors.decrypt,
        encrypt_pdf_processor=processors.encrypt,
        extract_pdf_image_processor=processors.extract_image,
        extract_pdf_text_processor=processors.extract_text,
        grayscale_pdf_processor=processors.grayscale,
        ocr_pdf_processor=processors.ocr,
        pdf_to_image_processor=processors.pdf_to_image,
        preview_pdf_processor=processors.preview_pdf,
        rename_pdf_processor=processors.rename,
        rotate_pdf_processor=processors.rotate,
        scale_pdf_processor=processors.scale,
        split_pdf_processor=processors.split,
        beautify_image_processor=processors.beautify,
        image_to_pdf_processor=processors.image_to_pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )

    compare = providers.Singleton(
        CompareHandlers,
        compare_service=services.compare,
        telegram_service=services.telegram,
    )
    feedback = providers.Singleton(
        FeedbackHandler,
        feedback_service=services.feedback,
        language_service=services.language,
        telegram_service=services.telegram,
    )
    image = providers.Singleton(
        BatchImageHandler,
        image_service=services.image,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    merge = providers.Singleton(
        MergeHandlers, merge_service=services.merge, telegram_service=services.telegram
    )
    text = providers.Singleton(
        TextHandlers, text_service=services.text, telegram_service=services.telegram
    )
    watermark = providers.Singleton(
        WatermarkHandlers,
        watermark_service=services.watermark,
        telegram_service=services.telegram,
    )
    webpage = providers.Singleton(
        WebpageHandler,
        webpage_service=services.webpage,
        language_service=services.language,
        telegram_service=services.telegram,
    )


class TelegramBot(containers.DeclarativeContainer):
    core = providers.DependenciesContainer()
    services = providers.DependenciesContainer()
    handlers = providers.DependenciesContainer()

    dispatcher = providers.Singleton(
        TelegramDispatcher,
        command_service=services.command,
        compare_handlers=handlers.compare,
        feedback_handler=handlers.feedback,
        file_handlers=handlers.file,
        image_handler=handlers.image,
        language_service=services.language,
        merge_handlers=handlers.merge,
        payment_service=services.payment,
        text_handlers=handlers.text,
        watermark_handlers=handlers.watermark,
        webpage_handler=handlers.webpage,
    )


class Application(containers.DeclarativeContainer):
    core = providers.Container(Core)
    clients = providers.Container(Clients)
    repositories = providers.Container(Repositories, clients=clients)
    services = providers.Container(Services, core=core, repositories=repositories)
    processors = providers.Container(Processors, services=services)
    handlers = providers.Container(Handlers, services=services, processors=processors)
    telegram_bot = providers.Container(
        TelegramBot, services=services, handlers=handlers
    )
