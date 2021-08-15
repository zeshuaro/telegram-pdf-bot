import os
import tempfile
from collections import defaultdict
from threading import Lock
from typing import List

import img2pdf
import noteshrink
from telegram import (
    ChatAction,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from pdf_bot.constants import BEAUTIFY, CANCEL, REMOVE_LAST, TEXT_FILTER, TO_PDF
from pdf_bot.language import set_lang
from pdf_bot.utils import (
    cancel,
    check_user_data,
    reply_with_cancel_btn,
    send_file_names,
    send_result_file,
)

WAIT_PHOTO = 0
PHOTO_IDS = "photo_ids"
PHOTO_NAMES = "photo_names"

photo_locks = defaultdict(Lock)


def photo_cov_handler() -> ConversationHandler:
    handlers = [
        MessageHandler(Filters.document | Filters.photo, check_photo),
        MessageHandler(TEXT_FILTER, check_text),
    ]
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("photo", photo)],
        states={
            WAIT_PHOTO: handlers,
            ConversationHandler.WAITING: handlers,
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    return conv_handler


def photo(update: Update, context: CallbackContext) -> int:
    update.effective_message.chat.send_action(ChatAction.TYPING)
    user_id = update.effective_message.from_user.id
    photo_locks[user_id].acquire()
    context.user_data[PHOTO_IDS] = []
    context.user_data[PHOTO_NAMES] = []
    photo_locks[user_id].release()

    return ask_first_photo(update, context)


def ask_first_photo(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    reply_with_cancel_btn(
        update,
        context,
        "{desc_1}\n\n{desc_2}".format(
            desc_1=_(
                "Send me the photos that you'll like to beautify "
                "or convert into a PDF file"
            ),
            desc_2=_(
                "Note that the photos will be beautified "
                "and converted in the order that you send me"
            ),
        ),
    )

    return WAIT_PHOTO


def check_photo(update: Update, context: CallbackContext) -> int:
    message = update.effective_message
    message.chat.send_action(ChatAction.TYPING)
    photo_file = check_photo_file(update, context)
    user_id = message.from_user.id
    photo_locks[user_id].acquire()

    if photo_file is None:
        if not context.user_data[PHOTO_IDS]:
            result = ask_first_photo(update, context)
        else:
            result = ask_next_photo(update, context)
    else:
        _ = set_lang(update, context)
        try:
            file_name = photo_file.file_name
        except AttributeError:
            file_name = _("File name unavailable")

        context.user_data[PHOTO_IDS].append(photo_file.file_id)
        context.user_data[PHOTO_NAMES].append(file_name)
        result = ask_next_photo(update, context)

    photo_locks[user_id].release()

    return result


def check_photo_file(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.document:
        photo_file = message.document
        if not photo_file.mime_type.startswith("image"):
            photo_file = None
            message.reply_text(_("Your file is not a photo"))
    else:
        photo_file = message.photo[-1]

    if photo_file is not None and photo_file.file_size > MAX_FILESIZE_DOWNLOAD:
        photo_file = None
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Your file is too large for me to download"),
                desc_2=_(
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                ),
            ),
        )

    return photo_file


def ask_next_photo(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    send_file_names(update, context, context.user_data[PHOTO_NAMES], _("photos"))
    reply_markup = ReplyKeyboardMarkup(
        [[_(BEAUTIFY), _(TO_PDF)], [_(REMOVE_LAST), _(CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    update.effective_message.reply_text(
        _(
            "Select the task from below if you've sent me all the photos, "
            "or keep sending me the photos"
        ),
        reply_markup=reply_markup,
    )

    return WAIT_PHOTO


def check_text(update: Update, context: CallbackContext) -> int:
    message = update.effective_message
    message.chat.send_action(ChatAction.TYPING)
    text = update.effective_message.text
    result = ConversationHandler.END
    _ = set_lang(update, context)

    if text in [_(REMOVE_LAST), _(BEAUTIFY), _(TO_PDF)]:
        user_id = message.from_user.id
        photo_locks[user_id].acquire()

        if not check_user_data(update, context, PHOTO_IDS):
            result = ConversationHandler.END
        else:
            if text == _(REMOVE_LAST):
                result = remove_photo(update, context)
            elif text in [_(BEAUTIFY), _(TO_PDF)]:
                result = process_all_photos(update, context)

        photo_locks[user_id].release()
    elif text == _(CANCEL):
        result = cancel(update, context)

    return result


def remove_photo(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    file_ids = context.user_data[PHOTO_IDS]
    file_names = context.user_data[PHOTO_NAMES]
    file_ids.pop()
    file_name = file_names.pop()

    update.effective_message.reply_text(
        _("{file_name} has been removed for beautifying or converting").format(
            file_name=f"<b>{file_name}</b>"
        ),
        parse_mode=ParseMode.HTML,
    )

    if len(file_ids) == 0:
        return ask_first_photo(update, context)
    else:
        return ask_next_photo(update, context)


def process_all_photos(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    file_ids = user_data[PHOTO_IDS]
    file_names = user_data[PHOTO_NAMES]

    if update.effective_message.text == BEAUTIFY:
        process_photo(update, context, file_ids, is_beautify=True)
    else:
        process_photo(update, context, file_ids, is_beautify=False)

    # Clean up memory
    if user_data[PHOTO_IDS] == file_ids:
        del user_data[PHOTO_IDS]
    if user_data[PHOTO_NAMES] == file_names:
        del user_data[PHOTO_NAMES]

    return ConversationHandler.END


def process_photo(
    update: Update, context: CallbackContext, file_ids: List[str], is_beautify: bool
) -> None:
    _ = set_lang(update, context)
    if is_beautify:
        update.effective_message.reply_text(
            _("Beautifying and converting your photos"),
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        update.effective_message.reply_text(
            _("Converting your photos into PDF"), reply_markup=ReplyKeyboardRemove()
        )

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(len(file_ids))]
    photo_files = []

    # Download all photos
    for i, file_id in enumerate(file_ids):
        file_name = temp_files[i].name
        photo_file = context.bot.get_file(file_id)
        photo_file.download(custom_path=file_name)
        photo_files.append(file_name)

    with tempfile.TemporaryDirectory() as dir_name:
        if is_beautify:
            out_fn = os.path.join(dir_name, "Beautified.pdf")
            noteshrink.notescan_main(
                photo_files, basename=f"{dir_name}/page", pdfname=out_fn
            )
            send_result_file(update, context, out_fn, "beautify")
        else:
            out_fn = os.path.join(dir_name, "Converted.pdf")
            with open(out_fn, "wb") as f:
                f.write(img2pdf.convert(photo_files))

            send_result_file(update, context, out_fn, "to_pdf")

    # Clean up files
    for tf in temp_files:
        tf.close()
