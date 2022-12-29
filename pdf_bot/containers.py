# pylint: disable=no-member


from dependency_injector import containers, providers
from requests import Session
from slack_sdk import WebClient
from telegram.ext import ExtBot
from telegram.request import HTTPXRequest

from pdf_bot.account import AccountRepository, AccountService
from pdf_bot.analytics import AnalyticsRepository, AnalyticsService
from pdf_bot.cli import CLIService
from pdf_bot.command import CommandService
from pdf_bot.compare import CompareHandlers, CompareService
from pdf_bot.feedback import FeedbackHandler, FeedbackRepository, FeedbackService
from pdf_bot.file_handler import FileHandler
from pdf_bot.image import ImageService
from pdf_bot.image_handler import BatchImageHandler
from pdf_bot.image_processor import (
    BeautifyImageProcessor,
    ImageTaskProcessor,
    ImageToPdfProcessor,
)
from pdf_bot.io import IOService
from pdf_bot.language import LanguageHandler, LanguageRepository, LanguageService
from pdf_bot.merge import MergeHandlers, MergeService
from pdf_bot.payment import PaymentService
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import (
    CompressPdfProcessor,
    CropPdfProcessor,
    DecryptPdfProcessor,
    EncryptPdfProcessor,
    ExtractPdfImageProcessor,
    ExtractPdfTextProcessor,
    GrayscalePdfProcessor,
    OcrPdfProcessor,
    PdfTaskProcessor,
    PdfToImageProcessor,
    PreviewPdfProcessor,
    RenamePdfProcessor,
    RotatePdfProcessor,
    ScalePdfProcessor,
    SplitPdfProcessor,
)
from pdf_bot.settings import Settings
from pdf_bot.telegram_dispatcher import TelegramDispatcher
from pdf_bot.telegram_internal import TelegramService
from pdf_bot.text import TextHandlers, TextRepository, TextService
from pdf_bot.watermark import WatermarkHandlers, WatermarkService
from pdf_bot.webpage import WebpageHandler, WebpageService


class Core(containers.DeclarativeContainer):
    settings = providers.Configuration(pydantic_settings=[Settings()])

    httpx_request = providers.Singleton(
        HTTPXRequest,
        connection_pool_size=settings.request_connection_pool_size,
        read_timeout=settings.request_read_timeout,
        write_timeout=settings.request_write_timeout,
        connect_timeout=settings.request_connect_timeout,
        pool_timeout=settings.request_pool_timeout,
    )
    telegram_bot = providers.Singleton(
        ExtBot,
        token=settings.telegram_token,
        arbitrary_callback_data=True,
        request=httpx_request,
    )


class Clients(containers.DeclarativeContainer):
    _settings = providers.Configuration(pydantic_settings=[Settings()])

    session = Session()
    session.hooks = {"response": lambda r, *args, **kwargs: r.raise_for_status()}

    api = providers.Object(session)
    slack = providers.Singleton(WebClient, token=_settings.slack_token)


class Repositories(containers.DeclarativeContainer):
    clients = providers.DependenciesContainer()

    account = providers.Singleton(AccountRepository)
    analytics = providers.Singleton(AnalyticsRepository, api_client=clients.api)
    feedback = providers.Singleton(FeedbackRepository, slack_client=clients.slack)
    language = providers.Singleton(LanguageRepository)
    text = providers.Singleton(TextRepository, api_client=clients.api)


class Services(containers.DeclarativeContainer):
    core = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    cli = providers.Singleton(CLIService)
    io = providers.Singleton(IOService)

    language = providers.Singleton(
        LanguageService, language_repository=repositories.language
    )

    account = providers.Singleton(
        AccountService,
        account_repository=repositories.account,
        language_service=language,
    )
    analytics = providers.Singleton(
        AnalyticsService,
        analytics_repository=repositories.analytics,
        language_service=language,
    )
    command = providers.Singleton(
        CommandService, account_service=account, language_service=language
    )
    telegram = providers.Singleton(
        TelegramService,
        io_service=io,
        language_service=language,
        analytics_service=analytics,
        bot=core.telegram_bot,
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

    image_task = providers.Singleton(
        ImageTaskProcessor,
        language_service=services.language,
    )
    pdf_task = providers.Singleton(
        PdfTaskProcessor,
        language_service=services.language,
    )

    compress = providers.Singleton(
        CompressPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    crop = providers.Singleton(
        CropPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    decrypt = providers.Singleton(
        DecryptPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    encrypt = providers.Singleton(
        EncryptPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    extract_image = providers.Singleton(
        ExtractPdfImageProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    extract_text = providers.Singleton(
        ExtractPdfTextProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    grayscale = providers.Singleton(
        GrayscalePdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    ocr = providers.Singleton(
        OcrPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    pdf_to_image = providers.Singleton(
        PdfToImageProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    preview_pdf = providers.Singleton(
        PreviewPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    rename = providers.Singleton(
        RenamePdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    rotate = providers.Singleton(
        RotatePdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    scale = providers.Singleton(
        ScalePdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    split = providers.Singleton(
        SplitPdfProcessor,
        pdf_service=services.pdf,
        telegram_service=services.telegram,
        language_service=services.language,
    )

    beautify = providers.Singleton(
        BeautifyImageProcessor,
        image_service=services.image,
        telegram_service=services.telegram,
        language_service=services.language,
    )
    image_to_pdf = providers.Singleton(
        ImageToPdfProcessor,
        image_service=services.image,
        telegram_service=services.telegram,
        language_service=services.language,
    )


class Handlers(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()
    processors = providers.DependenciesContainer()

    language = providers.Singleton(LanguageHandler, language_service=services.language)
    file = providers.Singleton(
        FileHandler,
        telegram_service=services.telegram,
        language_service=services.language,
        image_task_processor=processors.image_task,
        pdf_task_processor=processors.pdf_task,
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
