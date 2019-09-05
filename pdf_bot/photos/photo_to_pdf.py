import img2pdf
import noteshrink
import os
import tempfile

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import CANCEL, BEAUTIFY, CONVERT, WAIT_PHOTO_TASK
from pdf_bot.utils import cancel_with_async, send_file_names, send_result_file, check_user_data, \
    cancel_without_async
from pdf_bot.language import set_lang

WAIT_PHOTO = 0
PHOTO_ID = 'photo_id'
PHOTO_IDS = 'photo_ids'
PHOTO_NAMES = 'photo_names'


def photo_cov_handler():
    """
    Create the photo converting conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('photo', photo)],
        states={
            WAIT_PHOTO: [
                MessageHandler(Filters.document | Filters.photo, receive_photo),
                MessageHandler(Filters.text, check_photo_task)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_with_async)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def photo(update, context):
    """
    Start the photo converting conversation
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for a photo
    """
    # Clear previous photo info
    user_data = context.user_data
    if PHOTO_IDS in user_data:
        del user_data[PHOTO_IDS]
    if PHOTO_NAMES in user_data:
        del user_data[PHOTO_NAMES]

    _ = set_lang(update, context)
    update.effective_message.reply_text(_(
        'Send me the first photo that you\'ll like to beautify or convert into PDF format or '
        '/cancel this action.\n\n'
        'The photos will be beautified and converted in the order that you send me'))

    return WAIT_PHOTO


# Receive and check for the photo
@run_async
def receive_photo(update, context):
    """
    Validate the file and wait for the next action
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for a file or the conversation has ended
    """
    _ = set_lang(update, context)

    # Check if the photo has been sent as a document or photo
    if update.effective_message.document:
        photo_file = update.effective_message.document
        if not photo_file.mime_type.startswith('image'):
            update.effective_message.reply_text(_(
                'The file you sent is not a photo. '
                'Send me the photo that you\'ll like to beautify and convert'))

            return WAIT_PHOTO
    else:
        photo_file = update.effective_message.photo[-1]

    user_data = context.user_data
    if photo_file.file_size > MAX_FILESIZE_DOWNLOAD:
        text = _('The photo you sent is too large for me to download.\n\n')

        # Check if the user has already sent through some photos
        if PHOTO_NAMES in user_data and user_data[PHOTO_NAMES]:
            text += _('You can continue to beautify or convert with the files that you sent me, '
                      'or /cancel this action.')
            update.effective_message.reply_text(text)
            send_file_names(update, context, user_data[PHOTO_NAMES], _('photos'))

            return WAIT_PHOTO
        else:
            text += _('I can\'t convert your photos. Action cancelled')
            update.effective_message.reply_text(text)

            return ConversationHandler.END

    file_id = photo_file.file_id
    try:
        file_name = photo_file.file_name
    except AttributeError:
        file_name = _('File name unavailable')

    # Check if the user has already sent through some photos
    if PHOTO_IDS in user_data and user_data[PHOTO_IDS]:
        user_data[PHOTO_IDS].append(file_id)
        user_data[PHOTO_NAMES].append(file_name)
    else:
        user_data[PHOTO_IDS] = [file_id]
        user_data[PHOTO_NAMES] = [file_name]

    keyboard = [[_(BEAUTIFY), _(CONVERT)], [_(CANCEL)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.effective_message.reply_text(_(
        'Send me the next photo that you\'ll like to beautify or convert. '
        'Select the task from below if you have sent me all the photos.\n\n'
        'Note that I only have access to the file name if you sent your photo as a document'),
        reply_markup=reply_markup)
    send_file_names(update, context, user_data[PHOTO_NAMES], _('photos'))

    return WAIT_PHOTO


@run_async
def check_photo_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BEAUTIFY), _(CONVERT)]:
        return process_all_photos(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


def process_all_photos(update, context):
    """
    Process all photos
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
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
    """
    Beautify or convert the photos
    Args:
        update: the update object
        context: the context object
        file_ids: the list of file IDs
        is_beautify: the bool indicating if it is to beautify or convert the photos

    Returns:
        None
    """
    _ = set_lang(update, context)
    if is_beautify:
        update.effective_message.reply_text(_('Beautifying and converting your photos'),
                                            reply_markup=ReplyKeyboardRemove())
    else:
        update.effective_message.reply_text(_('Converting your photos'),
                                            reply_markup=ReplyKeyboardRemove())

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


def ask_photo_task(update, context, photo_file):
    _ = set_lang(update, context)
    message = update.effective_message

    if photo_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        message.reply_text(_('Your photo is too large for me to download. '
                             'I can\'t beautify or convert your photo'))

        return ConversationHandler.END

    context.user_data[PHOTO_ID] = photo_file.file_id
    keyboard = [[_(BEAUTIFY), _(CONVERT)], [_(CANCEL)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    message.reply_text(_('Select the task that you\'ll like to perform'), reply_markup=reply_markup)

    return WAIT_PHOTO_TASK


def process_photo_task(update, context):
    """
    Receive the task and perform the task on the photo
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    if not check_user_data(update, context, PHOTO_ID):
        return ConversationHandler.END

    _ = set_lang(update, context)
    user_data = context.user_data
    file_id = user_data[PHOTO_ID]

    if update.effective_message.text == _(BEAUTIFY):
        process_photo(update, context, [file_id], is_beautify=True)
    else:
        process_photo(update, context, [file_id], is_beautify=False)

    if user_data[PHOTO_ID] == file_id:
        del user_data[PHOTO_ID]

    return ConversationHandler.END
