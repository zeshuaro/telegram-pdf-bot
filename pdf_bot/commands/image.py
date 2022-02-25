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

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BEAUTIFY, CANCEL, REMOVE_LAST, TEXT_FILTER, TO_PDF
from pdf_bot.language import set_lang
from pdf_bot.utils import (
    cancel,
    check_user_data,
    reply_with_cancel_btn,
    send_file_names,
    send_result_file,
)

WAIT_IMAGE = 0
IMAGE_IDS = "image_ids"
IMAGE_NAMES = "image_names"

image_locks = defaultdict(Lock)


def image_cov_handler() -> ConversationHandler:
    handlers = [
        MessageHandler(Filters.document | Filters.photo, check_image),
        MessageHandler(TEXT_FILTER, check_text),
    ]
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("image", image)],
        states={
            WAIT_IMAGE: handlers,
            ConversationHandler.WAITING: handlers,
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    return conv_handler


def image(update: Update, context: CallbackContext) -> int:
    update.effective_message.chat.send_action(ChatAction.TYPING)
    user_id = update.effective_message.from_user.id
    image_locks[user_id].acquire()
    context.user_data[IMAGE_IDS] = []
    context.user_data[IMAGE_NAMES] = []
    image_locks[user_id].release()

    return ask_first_image(update, context)


def ask_first_image(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    reply_with_cancel_btn(
        update,
        context,
        "{desc_1}\n\n{desc_2}".format(
            desc_1=_(
                "Send me the images that you'll like to beautify or convert into a PDF "
                "file"
            ),
            desc_2=_(
                "Note that the images will be beautified and converted in the order "
                "that you send me"
            ),
        ),
    )

    return WAIT_IMAGE


def check_image(update: Update, context: CallbackContext) -> int:
    message = update.effective_message
    message.chat.send_action(ChatAction.TYPING)
    image_file = check_image_file(update, context)
    user_id = message.from_user.id
    image_locks[user_id].acquire()

    if image_file is None:
        if not context.user_data[IMAGE_IDS]:
            result = ask_first_image(update, context)
        else:
            result = ask_next_image(update, context)
    else:
        _ = set_lang(update, context)
        try:
            file_name = image_file.file_name
        except AttributeError:
            file_name = _("File name unavailable")

        context.user_data[IMAGE_IDS].append(image_file.file_id)
        context.user_data[IMAGE_NAMES].append(file_name)
        result = ask_next_image(update, context)

    image_locks[user_id].release()

    return result


def check_image_file(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.document:
        image_file = message.document
        if not image_file.mime_type.startswith("image"):
            image_file = None
            message.reply_text(_("Your file is not an image"))
    else:
        image_file = message.photo[-1]

    if image_file is not None and image_file.file_size > MAX_FILESIZE_DOWNLOAD:
        image_file = None
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Your file is too large for me to download and process"),
                desc_2=_(
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                ),
            ),
        )

    return image_file


def ask_next_image(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    send_file_names(update, context, context.user_data[IMAGE_NAMES], _("images"))
    reply_markup = ReplyKeyboardMarkup(
        [[_(BEAUTIFY), _(TO_PDF)], [_(REMOVE_LAST), _(CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    update.effective_message.reply_text(
        _(
            "Select the task from below if you've sent me all the images, or keep "
            "sending me the images"
        ),
        reply_markup=reply_markup,
    )

    return WAIT_IMAGE


def check_text(update: Update, context: CallbackContext) -> int:
    message = update.effective_message
    message.chat.send_action(ChatAction.TYPING)
    text = update.effective_message.text
    result = ConversationHandler.END
    _ = set_lang(update, context)

    if text in [_(REMOVE_LAST), _(BEAUTIFY), _(TO_PDF)]:
        user_id = message.from_user.id
        image_locks[user_id].acquire()

        if not check_user_data(update, context, IMAGE_IDS):
            result = ConversationHandler.END
        else:
            if text == _(REMOVE_LAST):
                result = remove_image(update, context)
            elif text in [_(BEAUTIFY), _(TO_PDF)]:
                result = process_all_images(update, context)

        image_locks[user_id].release()
    elif text == _(CANCEL):
        result = cancel(update, context)

    return result


def remove_image(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    file_ids = context.user_data[IMAGE_IDS]
    file_names = context.user_data[IMAGE_NAMES]
    file_ids.pop()
    file_name = file_names.pop()

    update.effective_message.reply_text(
        _("{file_name} has been removed for beautifying or converting").format(
            file_name=f"<b>{file_name}</b>"
        ),
        parse_mode=ParseMode.HTML,
    )

    if len(file_ids) == 0:
        return ask_first_image(update, context)

    return ask_next_image(update, context)


def process_all_images(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    file_ids = user_data[IMAGE_IDS]
    file_names = user_data[IMAGE_NAMES]

    if update.effective_message.text == BEAUTIFY:
        process_image(update, context, file_ids, is_beautify=True)
    else:
        process_image(update, context, file_ids, is_beautify=False)

    # Clean up memory
    if user_data[IMAGE_IDS] == file_ids:
        del user_data[IMAGE_IDS]
    if user_data[IMAGE_NAMES] == file_names:
        del user_data[IMAGE_NAMES]

    return ConversationHandler.END


def process_image(
    update: Update, context: CallbackContext, file_ids: List[str], is_beautify: bool
) -> None:
    _ = set_lang(update, context)
    if is_beautify:
        update.effective_message.reply_text(
            _("Beautifying and converting your images"),
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        update.effective_message.reply_text(
            _("Converting your images into PDF"), reply_markup=ReplyKeyboardRemove()
        )

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(len(file_ids))]
    image_files = []

    # Download all images
    for i, file_id in enumerate(file_ids):
        file_name = temp_files[i].name
        image_file = context.bot.get_file(file_id)
        image_file.download(custom_path=file_name)
        image_files.append(file_name)

    with tempfile.TemporaryDirectory() as dir_name:
        if is_beautify:
            out_fn = os.path.join(dir_name, "Beautified.pdf")
            noteshrink.notescan_main(
                image_files, basename=f"{dir_name}/page", pdfname=out_fn
            )
            send_result_file(update, context, out_fn, TaskType.beautify_image)
        else:
            out_fn = os.path.join(dir_name, "Converted.pdf")
            with open(out_fn, "wb") as f:
                f.write(img2pdf.convert(image_files))

            send_result_file(update, context, out_fn, TaskType.image_to_pdf)

    # Clean up files
    for tf in temp_files:
        tf.close()
