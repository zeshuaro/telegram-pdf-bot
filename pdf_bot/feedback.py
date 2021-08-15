import os

from dotenv import load_dotenv
from logbook import Logger
from slack import WebClient
from telegram import ChatAction, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)
from textblob import TextBlob
from textblob.exceptions import TranslatorError

from pdf_bot.constants import CANCEL, TEXT_FILTER
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel, reply_with_cancel_btn

load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")


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
    else:
        return receive_feedback(update, context)


def receive_feedback(update: Update, context: CallbackContext) -> int:
    message = update.effective_message
    tele_username = message.chat.username
    tele_id = message.chat.id
    feedback_msg = message.text
    feedback_lang = None
    b = TextBlob(feedback_msg)

    try:
        feedback_lang = b.detect_language()
    except TranslatorError:
        pass

    _ = set_lang(update, context)
    if feedback_lang is None or feedback_lang.lower() != "en":
        message.reply_text(_("The feedback is not in English, try again"))
        return 0

    text = f"Feedback received from @{tele_username} ({tele_id}):\n\n{feedback_msg}"
    success = False

    if SLACK_TOKEN is not None:
        client = WebClient(token=SLACK_TOKEN)
        response = client.chat_postMessage(channel="#pdf-bot-feedback", text=text)

        if response["ok"] and response["message"]["text"] == text:
            success = True

    if not success:
        log = Logger()
        log.notice(text)

    message.reply_text(
        _("Thank you for your feedback, I've already forwarded it to my developer")
    )

    return ConversationHandler.END
