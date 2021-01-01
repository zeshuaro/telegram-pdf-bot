import os

from dotenv import load_dotenv
from logbook import Logger
from slack import WebClient
from textblob import TextBlob
from textblob.exceptions import TranslatorError
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, Filters

from pdf_bot.constants import TEXT_FILTER
from pdf_bot.utils import cancel
from pdf_bot.language import set_lang

load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback, run_async=True)],
        states={0: [MessageHandler(TEXT_FILTER, receive_feedback, run_async=True)]},
        fallbacks=[CommandHandler("cancel", cancel, run_async=True)],
    )

    return conv_handler


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
            "Note that only English feedback will be forwarded to my developer."
        )
    )

    return 0


# Saves a feedback
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
    if not feedback_lang or feedback_lang.lower() != "en":
        message.reply_text(_("The feedback is not in English, try again"))

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
