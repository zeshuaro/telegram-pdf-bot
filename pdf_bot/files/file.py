from telegram import ReplyKeyboardMarkup
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_TASK, WAIT_DECRYPT_PW, WAIT_ENCRYPT_PW, WAIT_ROTATE_DEGREE, WAIT_SCALE_BY_X, \
    WAIT_SCALE_BY_Y, WAIT_SCALE_TO_X, WAIT_SCALE_TO_Y, WAIT_SPLIT_RANGE, WAIT_FILE_NAME, PDF_INFO
from pdf_bot.utils import cancel
from pdf_bot.files.crypto import ask_decrypt_pw, ask_encrypt_pw, decrypt_pdf, encrypt_pdf
from pdf_bot.files.rename import ask_pdf_new_name, rename_pdf
from pdf_bot.files.rotate import ask_rotate_degree, rotate_pdf
from pdf_bot.files.scale import ask_scale_x, ask_scale_by_y, ask_scale_to_y, pdf_scale_by, pdf_scale_to
from pdf_bot.files.split import ask_split_range, split_pdf
from pdf_bot.photos import get_pdf_cover, get_pdf_photos, pdf_to_photos, process_photo

PHOTO_ID = 'photo_id'


def file_cov_handler():
    """
    Create the file conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.document, check_doc), MessageHandler(Filters.photo, check_photo)],
        states={
            WAIT_TASK: [
                MessageHandler(Filters.regex(r'^Cover$'), get_pdf_cover),
                MessageHandler(Filters.regex(r'^Decrypt$'), ask_decrypt_pw),
                MessageHandler(Filters.regex(r'^Encrypt$'), ask_encrypt_pw),
                MessageHandler(Filters.regex(r'^Extract Images$'), get_pdf_photos),
                MessageHandler(Filters.regex(r'^To Images$'), pdf_to_photos),
                MessageHandler(Filters.regex(r'^Rotate$'), ask_rotate_degree),
                MessageHandler(Filters.regex(r'^Scale By$'), ask_scale_x),
                MessageHandler(Filters.regex(r'^Scale To$'), ask_scale_x),
                MessageHandler(Filters.regex(r'^Split$'), ask_split_range),
                MessageHandler(Filters.regex(r'^(Beautify|Convert)$'), receive_photo_task),
                MessageHandler(Filters.regex(r'^Rename$'), ask_pdf_new_name)
            ],
            WAIT_DECRYPT_PW: [MessageHandler(Filters.text, decrypt_pdf)],
            WAIT_ENCRYPT_PW: [MessageHandler(Filters.text, encrypt_pdf)],
            WAIT_ROTATE_DEGREE: [MessageHandler(Filters.regex(r'^(90|180|270)$'), rotate_pdf)],
            WAIT_SCALE_BY_X: [MessageHandler(Filters.text, ask_scale_by_y)],
            WAIT_SCALE_BY_Y: [MessageHandler(Filters.text, pdf_scale_by)],
            WAIT_SCALE_TO_X: [MessageHandler(Filters.text, ask_scale_to_y)],
            WAIT_SCALE_TO_Y: [MessageHandler(Filters.text, pdf_scale_to)],
            WAIT_SPLIT_RANGE: [MessageHandler(Filters.text, split_pdf)],
            WAIT_FILE_NAME: [MessageHandler(Filters.text, rename_pdf)]
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(Filters.regex('^Cancel$'), cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def check_doc(update, context):
    """
    Validate the document and wait for the next action
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the next action or the conversation has ended
    """
    doc = update.message.document
    mime_type = doc.mime_type

    if mime_type.startswith('image'):
        return check_photo(update, context, doc)
    elif not mime_type.endswith('pdf'):
        return ConversationHandler.END
    elif doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text('Your PDF file you sent is too large for me to download. '
                                  'I can\'t perform any tasks on it.')

        return ConversationHandler.END

    context.user_data[PDF_INFO] = doc.file_id, doc.file_name
    keywords = sorted(['Decrypt', 'Encrypt', 'Rotate', 'Scale By', 'Scale To', 'Split', 'Cover', 'To Images',
                       'Extract Images', 'Rename'])
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append(['Cancel'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Select the task that you\'ll like to perform.', reply_markup=reply_markup)

    return WAIT_TASK


@run_async
def check_photo(update, context, photo_file=None):
    """
    Validate the photo and wait for the next action
    Args:
        update: the update object
        context: the context object
        photo_file: the photo file object

    Returns:
        The variable indicating to wait for the next action or the conversation has ended
    """
    if photo_file is None:
        photo_file = update.message.photo[-1]

    if photo_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text('Your photo is too large for me to download. '
                                  'I can\'t beautify or convert your photo.')

        return ConversationHandler.END

    context.user_data[PHOTO_ID] = photo_file.file_id
    keyboard = [['Beautify', 'Convert'], ['Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Select the task that you\'ll like to perform.', reply_markup=reply_markup)

    return WAIT_TASK


@run_async
def receive_photo_task(update, context):
    """
    Receive the task and perform the task on the photo
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if PHOTO_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PHOTO_ID]
    if update.message.text.lower() == 'beautify':
        process_photo(update, context, [file_id], is_beautify=True)
    else:
        process_photo(update, context, [file_id], is_beautify=False)

    if user_data[PHOTO_ID] == file_id:
        del user_data[PHOTO_ID]

    return ConversationHandler.END
