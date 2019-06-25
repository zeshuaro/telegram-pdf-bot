import shlex
import tempfile

from logbook import Logger
from subprocess import Popen, PIPE
from telegram import ChatAction
from telegram.constants import MAX_FILESIZE_UPLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from constants import *
from utils import check_pdf, cancel


# Create a compare conversation handler
def compare_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('compare', compare)],
        states={
            WAIT_FIRST_COMPARE_FILE: [MessageHandler(Filters.document, check_first_compare_file, pass_user_data=True)],
            WAIT_SECOND_COMPARE_FILE: [MessageHandler(Filters.document, check_second_compare_file,
                                                      pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    return conv_handler


# Start the compare conversation
@run_async
def compare(bot, update):
    update.message.reply_text('Please send me one of the PDF files that you will like to compare or type /cancel to '
                              'cancel this operation.\n\nPlease note that I can only look for text differences.')

    return WAIT_FIRST_COMPARE_FILE


# Receive and check for the first PDF file
@run_async
def check_first_compare_file(bot, update, user_data):
    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_FIRST_COMPARE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    user_data['compare_file_id'] = update.message.document.file_id
    update.message.reply_text('Please send me the other PDF file that you will like to compare.')

    return WAIT_SECOND_COMPARE_FILE


# Receive and check for the second PDF file
# If success, compare the two PDF files
@run_async
def check_second_compare_file(bot, update, user_data):
    if 'compare_file_id' not in user_data:
        return ConversationHandler.END

    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_SECOND_COMPARE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    return compare_pdf(bot, update, user_data, update.message.document.file_id)


# Compare two PDF files
def compare_pdf(bot, update, user_data, second_file_id):
    if 'compare_file_id' not in user_data:
        return ConversationHandler.END

    first_file_id = user_data['compare_file_id']
    update.message.reply_text('Comparing your PDF files...')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Compared_', suffix='.png'))
    first_filename, second_filename, out_filename = [x.name for x in temp_files]

    # Download PDF files
    first_pdf_file = bot.get_file(first_file_id)
    first_pdf_file.download(custom_path=first_filename)
    second_pdf_file = bot.get_file(second_file_id)
    second_pdf_file.download(custom_path=second_filename)

    # Run pdf-diff
    command = f'pdf-diff {first_filename} {second_filename}'
    proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    proc_out, proc_err = proc.communicate()

    if proc.returncode != 0:
        log = Logger()
        if 'there are no text difference' in proc_err.decode('utf8').strip().lower():
            update.message.reply_text('There are no differences between the two PDF files you sent me.')
        else:
            log.error(proc_err.decode('utf8'))
            update.message.reply_text('Something went wrong, please try again. '
                                      'Please make sure that the PDF files are not encrypted.')
    else:
        with open(out_filename, 'wb') as f:
            f.write(proc_out)

        if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
            update.message.reply_text('The difference result file is too large for me to send to you, sorry.')
        else:
            update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
            update.message.reply_photo(photo=open(out_filename, 'rb'),
                                       caption='Here are the differences between your PDF files.')

    # Clean up memory and files
    if user_data['compare_file_id'] == first_file_id:
        del user_data['compare_file_id']
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END