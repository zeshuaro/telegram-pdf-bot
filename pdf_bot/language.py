import gettext

from google.cloud import datastore
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.chataction import ChatAction
from telegram.ext import CallbackContext

from pdf_bot.consts import LANGUAGE, LANGUAGES, USER
from pdf_bot.db import db


def send_lang(update: Update, context: CallbackContext, query: CallbackQuery = None):
    update.effective_message.reply_chat_action(ChatAction.TYPING)
    lang = get_lang(update, context, query)
    langs = [
        InlineKeyboardButton(key, callback_data=key)
        for key, value in sorted(LANGUAGES.items(), key=lambda x: x[1])
        if value != lang
    ]
    keyboard_size = 2
    keyboard = [
        langs[i : i + keyboard_size] for i in range(0, len(langs), keyboard_size)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Select your language"), reply_markup=reply_markup
    )


def get_lang(update: Update, context: CallbackContext, query: CallbackQuery = None):
    if context.user_data is not None and LANGUAGE in context.user_data:
        lang = context.user_data[LANGUAGE]
    else:
        if query is None:
            sender = update.effective_message.from_user or update.effective_chat
            user_id = sender.id
        else:
            user_id = query.from_user.id

        user_key = db.key(USER, user_id)
        user = db.get(key=user_key)

        if user is None or LANGUAGE not in user:
            lang = "en_GB"
        else:
            lang = user[LANGUAGE]
            if lang == "en":
                lang = "en_GB"

        if context.user_data is not None:
            context.user_data[LANGUAGE] = lang

    return lang


def store_lang(update, context, query):
    lang_code = LANGUAGES[query.data]
    with db.transaction():
        user_key = db.key(USER, query.from_user.id)
        user = db.get(key=user_key)
        if user is None:
            user = datastore.Entity(user_key)
        user[LANGUAGE] = lang_code
        db.put(user)

    context.user_data[LANGUAGE] = lang_code
    _ = set_lang(update, context)
    query.message.edit_text(
        _("Your language has been set to {language}").format(language=query.data)
    )


def set_lang(update, context, query=None):
    lang = get_lang(update, context, query)
    t = gettext.translation("pdf_bot", localedir="locale", languages=[lang])

    return t.gettext
