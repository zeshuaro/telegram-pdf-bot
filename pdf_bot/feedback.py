import os

from dotenv import load_dotenv
from logbook import Logger
from slack import WebClient
from textblob import TextBlob
from textblob.exceptions import TranslatorError
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.utils import cancel_with_async
from pdf_bot.language import set_lang

load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
VALID_LANGS = ("en", "zh-hk", "zh-tw", "zh-cn")


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback)],
        states={0: [MessageHandler(Filters.text & ~Filters.command, receive_feedback)]},
        fallbacks=[CommandHandler("cancel", cancel_with_async)],
    )

    return conv_handler


@run_async
def feedback(update, context):
    """
    Start the feedback conversation
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for feedback
    """
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _(
            "Send me your feedback or /cancel this action. "
            "My developer can understand English and Chinese"
        )
    )

    return 0


# Saves a feedback
@run_async
def receive_feedback(update, context):
    """
    Log the feedback on Slack
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
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
    if not feedback_lang or feedback_lang.lower() not in VALID_LANGS:
        message.reply_text(_("The feedback is not in English or Chinese, try again"))

        return 0

    text = "Feedback received from @{} ({}):\n\n{}".format(
        tele_username, tele_id, feedback_msg
    )
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
