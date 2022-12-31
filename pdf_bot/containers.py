# pylint: disable=no-member


from dependency_injector import containers, providers
from requests import Session
from slack_sdk import WebClient as SlackClient
from telegram.ext import AIORateLimiter, ExtBot
from telegram.request import HTTPXRequest

from pdf_bot.account import AccountRepository, AccountService
from pdf_bot.analytics import AnalyticsRepository, AnalyticsService
from pdf_bot.cli import CLIService
from pdf_bot.command import CommandService, MyCommandHandler
from pdf_bot.compare import CompareHandler, CompareService
from pdf_bot.datastore import MyDatastoreClient
from pdf_bot.error import ErrorCallbackQueryHandler, ErrorHandler, ErrorService
from pdf_bot.feedback import FeedbackHandler, FeedbackRepository, FeedbackService
from pdf_bot.file import FileHandler, FileService
from pdf_bot.image import ImageService
from pdf_bot.image_handler import BatchImageHandler, BatchImageService
from pdf_bot.image_processor import BeautifyImageProcessor, ImageTaskProcessor, ImageToPdfProcessor
from pdf_bot.io import IOService
from pdf_bot.language import LanguageHandler, LanguageRepository, LanguageService
from pdf_bot.log import InterceptLoggingHandler, MyLogHandler
from pdf_bot.merge import MergeHandler, MergeService
from pdf_bot.payment import PaymentHandler, PaymentService
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
from pdf_bot.telegram_internal import TelegramService
from pdf_bot.text import TextHandler, TextRepository, TextService
from pdf_bot.watermark import WatermarkHandler, WatermarkService
from pdf_bot.webpage import WebpageHandler, WebpageService


class Core(containers.DeclarativeContainer):
    settings = providers.Configuration(pydantic_settings=[Settings()])

    _bot_request = providers.Singleton(
        HTTPXRequest,
        connection_pool_size=settings.request_connection_pool_size,
        read_timeout=settings.request_read_timeout,
        write_timeout=settings.request_write_timeout,
        connect_timeout=settings.request_connect_timeout,
        pool_timeout=settings.request_pool_timeout,
    )
    _bot_rate_limiter = providers.Singleton(AIORateLimiter)

    telegram_bot = providers.Singleton(
        ExtBot,
        token=settings.telegram_token,
        arbitrary_callback_data=True,
        request=_bot_request,
        rate_limiter=_bot_rate_limiter,
    )

    intercept_logging_handler = providers.Singleton(InterceptLoggingHandler)
    log_handler = providers.Singleton(
        MyLogHandler, intercept_logging_handler=intercept_logging_handler
    )


class Clients(containers.DeclarativeContainer):
    _settings = providers.Configuration(pydantic_settings=[Settings()])

    _session = Session()
    _session.hooks = {
        "response": lambda r, *_args, **_kwargs: r.raise_for_status()  # pragma: no cover
    }

    api = providers.Object(_session)
    datastore = providers.Singleton(MyDatastoreClient, _settings.gcp_service_account)
    slack = providers.Singleton(SlackClient, token=_settings.slack_token)


class Repositories(containers.DeclarativeContainer):
    _settings = providers.Configuration(pydantic_settings=[Settings()])
    clients = providers.DependenciesContainer()

    account = providers.Singleton(AccountRepository, datastore_client=clients.datastore)
    analytics = providers.Singleton(AnalyticsRepository, api_client=clients.api, settings=_settings)
    feedback = providers.Singleton(FeedbackRepository, slack_client=clients.slack)
    language = providers.Singleton(LanguageRepository, datastore_client=clients.datastore)
    text = providers.Singleton(
        TextRepository,
        api_client=clients.api,
        google_fonts_token=_settings.google_fonts_token,
    )


class Services(containers.DeclarativeContainer):
    _settings = providers.Configuration(pydantic_settings=[Settings()])
    core = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    cli = providers.Singleton(CLIService)
    io = providers.Singleton(IOService)

    language = providers.Singleton(LanguageService, language_repository=repositories.language)

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
    error = providers.Singleton(ErrorService, language_service=language)
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
    pdf = providers.Singleton(PdfService, cli_service=cli, io_service=io, telegram_service=telegram)

    _image_task = providers.Singleton(ImageTaskProcessor, language_service=language)
    _pdf_task = providers.Singleton(PdfTaskProcessor, language_service=language)
    file = providers.Singleton(
        FileService,
        telegram_service=telegram,
        language_service=language,
        image_task_processor=_image_task,
        pdf_task_processor=_pdf_task,
    )

    compare = providers.Singleton(
        CompareService,
        pdf_service=pdf,
        telegram_service=telegram,
        language_service=language,
    )
    feedback = providers.Singleton(
        FeedbackService,
        feedback_repository=repositories.feedback,
        telegram_service=telegram,
        language_service=language,
    )
    batch_image = providers.Singleton(
        BatchImageService,
        image_service=image,
        telegram_service=telegram,
        language_service=language,
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
        telegram_service=telegram,
        stripe_token=_settings.stripe_token,
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
    webpage = providers.Singleton(
        WebpageService,
        io_service=io,
        telegram_service=telegram,
        language_service=language,
    )


class Processors(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()

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
    _settings = providers.Configuration(pydantic_settings=[Settings()])
    services = providers.DependenciesContainer()

    error = providers.Singleton(ErrorHandler, language_service=services.language)

    # Make sure payment handler comes first as it contains handlers that need to be
    # priortised
    payment = providers.Singleton(PaymentHandler, payment_service=services.payment)
    command = providers.Singleton(
        MyCommandHandler,
        command_service=services.command,
        admin_telegram_id=_settings.admin_telegram_id,
    )
    language = providers.Singleton(LanguageHandler, language_service=services.language)

    # Make sure webpage handler comes before the file processors to capture the URLs
    webpage = providers.Singleton(WebpageHandler, webpage_service=services.webpage)

    file = providers.Singleton(
        FileHandler, file_service=services.file, telegram_service=services.telegram
    )

    compare = providers.Singleton(
        CompareHandler,
        compare_service=services.compare,
        telegram_service=services.telegram,
    )
    feedback = providers.Singleton(
        FeedbackHandler,
        feedback_service=services.feedback,
        telegram_service=services.telegram,
    )
    image = providers.Singleton(
        BatchImageHandler,
        batch_image_service=services.batch_image,
        telegram_service=services.telegram,
    )
    merge = providers.Singleton(
        MergeHandler, merge_service=services.merge, telegram_service=services.telegram
    )
    text = providers.Singleton(
        TextHandler, text_service=services.text, telegram_service=services.telegram
    )
    watermark = providers.Singleton(
        WatermarkHandler,
        watermark_service=services.watermark,
        telegram_service=services.telegram,
    )

    # This is the catch all callback query handler so make sure it comes last
    error_callback_query = providers.Singleton(
        ErrorCallbackQueryHandler, error_service=services.error
    )


class Application(containers.DeclarativeContainer):
    core = providers.Container(Core)
    clients = providers.Container(Clients)
    repositories = providers.Container(Repositories, clients=clients)
    services = providers.Container(Services, core=core, repositories=repositories)
    processors = providers.Container(Processors, services=services)
    handlers = providers.Container(Handlers, services=services)
