import asyncio
import os

import cld3
from dotenv import load_dotenv
from logbook import Logger
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient
from telegram import ChatAction, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.consts import CANCEL, TEXT_FILTER
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel, reply_with_cancel_btn

load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

slack_client = AsyncWebClient(SLACK_TOKEN)


def feedback_cov_handler() -> ConversationHandler:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback)],
        states={0: [MessageHandler(TEXT_FILTER, check_text)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    return conv_handler


def feedback(update: Update, context: CallbackContext) -> int:
    """
    Start the feedback conversation
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for feedback
    """
    update.effective_message.chat.send_action(ChatAction.TYPING)
    _ = set_lang(update, context)
    text = _(
        "Send me your feedback (only English feedback will be "
        "forwarded to my developer)"
    )
    reply_with_cancel_btn(update, context, text)

    return 0


def check_text(update: Update, context: CallbackContext) -> int:
    update.effective_message.chat.send_action(ChatAction.TYPING)
    _ = set_lang(update, context)
    if update.effective_message.text == _(CANCEL):
        return cancel(update, context)

    return receive_feedback(update, context)


def receive_feedback(update: Update, context: CallbackContext) -> int:
    message = update.effective_message
    feedback_msg = message.text
    feedback_lang = cld3.get_language(feedback_msg)  # pylint: disable=no-member

    _ = set_lang(update, context)
    if feedback_lang.language.lower() == "en":
        text = (
            f"Feedback received from @{message.chat.username} ({message.chat.id}):\n\n"
            f"{feedback_msg}"
        )
        asyncio.run(post_message(text))
        message.reply_text(
            _("Thank you for your feedback, I've already forwarded it to my developer")
        )

        return ConversationHandler.END

    message.reply_text(_("The feedback is not in English, try again"))
    return 0


async def post_message(text):
    try:
        await slack_client.chat_postMessage(channel="#pdf-bot-feedback", text=text)
    except SlackApiError as e:
        log = Logger()
        log.error(f"Failed to send Slack message: {e.response['error']}")
