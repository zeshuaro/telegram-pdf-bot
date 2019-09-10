import img2pdf
import noteshrink
import os
import tempfile

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import CANCEL, BEAUTIFY, TO_PDF, REMOVE_LAST
from pdf_bot.utils import cancel_with_async, send_file_names, send_result_file, check_user_data, \
    cancel_without_async
from pdf_bot.language import set_lang

WAIT_PHOTO = 0
PHOTO_IDS = 'photo_ids'
PHOTO_NAMES = 'photo_names'


def photo_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('photo', photo)],
        states={
            WAIT_PHOTO: [
                MessageHandler(Filters.document | Filters.photo, check_photo),
                MessageHandler(Filters.text, check_text)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_with_async)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def photo(update, context):
    context.user_data[PHOTO_IDS] = []
    context.user_data[PHOTO_NAMES] = []

    return ask_first_photo(update, context)


def ask_first_photo(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup([[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the first photo that you\'ll like to beautify or convert into PDF\n\n'
        'Note that the photos will be beautified and converted in the order that you send me'),
        reply_markup=reply_markup)
    
    return WAIT_PHOTO


@run_async
def check_photo(update, context):
    _ = set_lang(update, context)
    photo_file = check_photo_file(update, context)

    if photo_file is None:
        if not context.user_data[PHOTO_IDS]:
            return ask_first_photo(update, context)
        else:
            return ask_next_photo(update, context)

    try:
        file_name = photo_file.file_name
    except AttributeError:
        file_name = _('File name unavailable')

    context.user_data[PHOTO_IDS].append(photo_file.file_id)
    context.user_data[PHOTO_NAMES].append(file_name)

    return ask_next_photo(update, context)


def check_photo_file(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    
    if message.document:
        photo_file = message.document
        if not photo_file.mime_type.startswith('image'):
            photo_file = None
            message.reply_text(_(
                'The file you\'ve sent is not a photo'))
    else:
        photo_file = message.photo[-1]

    if photo_file is not None and photo_file.file_size > MAX_FILESIZE_DOWNLOAD:
        photo_file = None
        message.reply_text(_('The photo you\'ve sent is too large for me to download'))

    return photo_file


def ask_next_photo(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(BEAUTIFY), _(TO_PDF)], [_(REMOVE_LAST), _(CANCEL)]], resize_keyboard=True,
        one_time_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the next photo that you\'ll like to beautify or convert to PDF\n\n'
        'Select the task from below if you have sent me all the photos'),
        reply_markup=reply_markup)
    send_file_names(update, context, context.user_data[PHOTO_NAMES], _('photos'))

    return WAIT_PHOTO


@run_async
def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(REMOVE_LAST):
        return remove_photo(update, context)
    if text in [_(BEAUTIFY), _(TO_PDF)]:
        return process_all_photos(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


def remove_photo(update, context):
    if not check_user_data(update, context, PHOTO_IDS):
        return ConversationHandler.END

    _ = set_lang(update, context)
    file_ids = context.user_data[PHOTO_IDS]
    file_names = context.user_data[PHOTO_NAMES]
    file_ids.pop()
    file_name = file_names.pop()

    update.effective_message.reply_text(_(
        '*{}* has been removed for beautifying or converting').format(file_name),
        parse_mode=ParseMode.MARKDOWN)

    if len(file_ids) == 0:
        return ask_first_photo(update, context)
    else:
        return ask_next_photo(update, context)


def process_all_photos(update, context):
    if not check_user_data(update, context, PHOTO_IDS):
        return ConversationHandler.END

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


def process_photo(update, context, file_ids, is_beautify):
    _ = set_lang(update, context)
    if is_beautify:
        update.effective_message.reply_text(_(
            'Beautifying and converting your photos'), reply_markup=ReplyKeyboardRemove())
    else:
        update.effective_message.reply_text(_(
            'Converting your photos into PDF'), reply_markup=ReplyKeyboardRemove())

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
            out_fn = os.path.join(dir_name, 'Beautified.pdf')
            noteshrink.notescan_main(photo_files, basename=f'{dir_name}/page', pdfname=out_fn)
            send_result_file(update, context, out_fn, 'beautify')
        else:
            out_fn = os.path.join(dir_name, 'Converted.pdf')
            with open(out_fn, 'wb') as f:
                f.write(img2pdf.convert(photo_files))

            send_result_file(update, context, out_fn, 'convert')

    # Clean up files
    for tf in temp_files:
        tf.close()
