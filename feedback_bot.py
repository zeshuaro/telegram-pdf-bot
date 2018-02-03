#!/usr/bin/env python3

import dotenv
import logging
import os

from textblob import TextBlob
from textblob.exceptions import TranslatorError
from slackclient import SlackClient
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async


dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

BOT_NAME = "PDF Bot"  # Bot name to be appeared in your Slack Channel
VALID_LANGS = ("en", "zh-hk", "zh-tw", "zh-cn")


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],
        states={0: [MessageHandler(Filters.text, receive_feedback)]},
        fallbacks=[CommandHandler("cancel", cancel_feedback)]
    )

    return conv_handler


# Sends a feedback message
@run_async
def feedback(bot, update):
    text = "Please send me your feedback or type /cancel to cancel this operation. " \
           "My developer can understand English and Chinese."
    update.message.reply_text(text)

    return 0


# Saves a feedback
@run_async
def receive_feedback(bot, update):
    tele_username = update.message.chat.username
    tele_id = update.message.chat.id
    feedback_msg = update.message.text
    feedback_lang = None
    b = TextBlob(feedback_msg)

    try:
        feedback_lang = b.detect_language()
    except TranslatorError:
        pass

    if not feedback_lang or feedback_lang.lower() not in VALID_LANGS:
        update.message.reply_text("The feedback you sent is not in English or Chinese. Please try again.")
        return 0

    text = "Feedback received from @{} ({})\n\n{}".format(tele_username, tele_id, feedback_msg)
    if SLACK_TOKEN:
        sc = SlackClient(SLACK_TOKEN)
        sc.api_call(
            "chat.postMessage",
            channel="#bots_feedback",
            text="{} Feedback".format(BOT_NAME),
            attachments=[{
                "text": text
            }]
        )
    else:
        logger = logging.getLogger(__name__)
        logger.info(text)

    update.message.reply_text("Thank you for your feedback, I've already forwarded it to my developer.")

    return ConversationHandler.END


# Cancels feedback operation
@run_async
def cancel_feedback(bot, update):
    update.message.reply_text("Feedback operation cancelled.")
    return ConversationHandler.END
