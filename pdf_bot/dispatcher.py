import os

from dependency_injector.wiring import Provide, inject
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PreCheckoutQueryHandler,
)
from telegram.ext.dispatcher import Dispatcher

from pdf_bot.command.command_service import CommandService
from pdf_bot.compare import CompareHandlers
from pdf_bot.consts import CHANNEL_NAME, LANGUAGES, PAYMENT, SET_LANG
from pdf_bot.containers import Application
from pdf_bot.feedback import feedback_cov_handler
from pdf_bot.file import FileHandlers
from pdf_bot.image import ImageHandlers
from pdf_bot.language import send_lang, set_lang, store_lang
from pdf_bot.merge import MergeHandlers
from pdf_bot.payment import (
    precheckout_check,
    send_payment_invoice,
    send_support_options,
    successful_payment,
)
from pdf_bot.text import TextHandlers
from pdf_bot.url import url_to_pdf
from pdf_bot.watermark import WatermarkHandlers

load_dotenv()
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")
CALLBACK_DATA = "callback_data"


@inject
def setup_dispatcher(
    dispatcher: Dispatcher,
    command_service: CommandService = Provide[
        Application.services.command  # pylint: disable=no-member
    ],
    compare_handlers: CompareHandlers = Provide[
        Application.handlers.compare  # pylint: disable=no-member
    ],
    file_handlers: FileHandlers = Provide[
        Application.handlers.file  # pylint: disable=no-member
    ],
    image_handlers: ImageHandlers = Provide[
        Application.handlers.image  # pylint: disable=no-member
    ],
    merge_handlers: MergeHandlers = Provide[
        Application.handlers.merge  # pylint: disable=no-member
    ],
    text_handlers: TextHandlers = Provide[
        Application.handlers.text  # pylint: disable=no-member
    ],
    watermark_handlers: WatermarkHandlers = Provide[
        Application.handlers.watermark  # pylint: disable=no-member
    ],
):
    dispatcher.add_handler(
        CommandHandler(
            "start", send_support_options, Filters.regex("support"), run_async=True
        )
    )
    dispatcher.add_handler(
        CommandHandler("start", command_service.send_start_message, run_async=True)
    )

    dispatcher.add_handler(CommandHandler("help", help_msg, run_async=True))
    dispatcher.add_handler(CommandHandler("setlang", send_lang, run_async=True))
    dispatcher.add_handler(
        CommandHandler("support", send_support_options, run_async=True)
    )

    # Callback query handler
    dispatcher.add_handler(CallbackQueryHandler(process_callback_query, run_async=True))

    # Payment handlers
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_check, run_async=True))
    dispatcher.add_handler(
        MessageHandler(Filters.successful_payment, successful_payment, run_async=True)
    )

    # URL handler
    dispatcher.add_handler(
        MessageHandler(Filters.entity(MessageEntity.URL), url_to_pdf, run_async=True)
    )

    # PDF commands handlers
    dispatcher.add_handler(compare_handlers.conversation_handler())
    dispatcher.add_handler(merge_handlers.conversation_handler())
    dispatcher.add_handler(image_handlers.conversation_handler())
    dispatcher.add_handler(text_handlers.conversation_handler())
    dispatcher.add_handler(watermark_handlers.conversation_handler())

    # PDF file handler
    dispatcher.add_handler(file_handlers.conversation_handler())

    # Feedback handler
    dispatcher.add_handler(feedback_cov_handler())

    # Admin commands handlers
    if ADMIN_TELEGRAM_ID is not None:
        dispatcher.add_handler(
            CommandHandler("send", send_msg, Filters.user(int(ADMIN_TELEGRAM_ID)))
        )

    # Log all errors
    dispatcher.add_error_handler(error_callback)


def help_msg(update, context):
    _ = set_lang(update, context)
    keyboard = [
        [InlineKeyboardButton(_("Set Language 🌎"), callback_data=SET_LANG)],
        [
            InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
            InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.effective_message.reply_text(
        "{desc_1}\n{pdf_files}\n{images}\n{webpage_links}\n\n{desc_2}\n"
        "{compare_desc}\n{merge_desc}\n{image_desc}\n{text_desc}\n"
        "{watermark_desc}".format(
            desc_1=_(
                "You can perform most of the tasks by sending me one of the followings:"
            ),
            pdf_files=_("- PDF files"),
            images=_("- Images"),
            webpage_links=_("- Webpage links"),
            desc_2=_(
                "The rest of the tasks can be performed by using the following "
                "commands:"
            ),
            compare_desc=_("{command} - compare PDF files").format(command="/compare"),
            merge_desc=_("{command} - merge PDF files").format(command="/merge"),
            image_desc=_(
                "{command} - convert and combine multiple images into PDF files"
            ).format(command="/image"),
            text_desc=_("{command} - create PDF files from text messages").format(
                command="/text"
            ),
            watermark_desc=_("{command} - add watermark to PDF files").format(
                command="/watermark"
            ),
        ),
        reply_markup=reply_markup,
    )


def process_callback_query(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    query = update.callback_query
    data = query.data

    if CALLBACK_DATA not in context.user_data:
        context.user_data[CALLBACK_DATA] = set()

    if data not in context.user_data[CALLBACK_DATA]:
        context.user_data[CALLBACK_DATA].add(data)
        if data == SET_LANG:
            send_lang(update, context, query)
        elif data in LANGUAGES:
            store_lang(update, context, query)
        if data == PAYMENT:
            send_support_options(update, context, query)
        elif data.startswith("payment,"):
            send_payment_invoice(update, context, query)

        context.user_data[CALLBACK_DATA].remove(data)

    try:
        query.answer()
    except BadRequest as e:
        if e.message.startswith("Query is too old"):
            context.bot.send_message(
                query.from_user.id,
                _(
                    "The button has expired, please try again with a new message/query "
                    "then press the new button"
                ),
            )
        else:
            raise


def send_msg(update: Update, context: CallbackContext):
    tele_id = int(context.args[0])
    message = " ".join(context.args[1:])

    try:
        context.bot.send_message(tele_id, message)
        update.effective_message.reply_text("Message sent")
    except Unauthorized:
        update.effective_message.reply_text("User has blocked the bot")


def error_callback(_update: Update, context: CallbackContext):
    try:
        raise context.error
    except Unauthorized:
        pass
