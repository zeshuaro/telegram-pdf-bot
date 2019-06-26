import tempfile

from PyPDF2 import PdfFileWriter
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from constants import WAIT_WATERMARK_SOURCE_FILE, WAIT_WATERMARK_FILE, PDF_INVALID_FORMAT, PDF_OK
from utils import cancel, check_pdf, open_pdf, send_result

WATERMARK_ID = 'watermark_id'


def watermark_cov_handler():
    """
    Create the watermark conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('watermark', watermark)],
        states={
            WAIT_WATERMARK_SOURCE_FILE: [MessageHandler(Filters.document, receive_source_file,
                                                        pass_user_data=True)],
            WAIT_WATERMARK_FILE: [MessageHandler(Filters.document, receive_watermark_file)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def watermark(update, context):
    """
    Start the watermark conversation
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the source PDF file
    """
    update.message.reply_text('Please send me the PDF file that you will like to add a watermark or type /cancel to '
                              'cancel this operation.')

    return WAIT_WATERMARK_SOURCE_FILE


@run_async
def receive_source_file(update, context):
    """
    Validate the file and wait for the watermark file
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for the watermark file or the conversation has ended
    """
    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WATERMARK_SOURCE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    user_data[WATERMARK_ID] = update.message.document.file_id
    update.message.reply_text('Please send me the watermark in PDF format.')

    return WAIT_WATERMARK_FILE


# Receive and check for the watermark PDF file and watermark the PDF file
@run_async
def receive_watermark_file(update, context):
    """
    Validate the file and add the watermark onto the source PDF file
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for the watermark file or the conversation has ended
    """
    if WATERMARK_ID not in user_data:
        return ConversationHandler.END

    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WATERMARK_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    return add_pdf_watermark(context.bot, update, update.message.document.file_id)


def add_pdf_watermark(bot, update, watermark_file_id):
    """
    Add watermark onto the PDF file
    Args:
        bot: the bot object
        update: the update object
        user_data: the dict of user data
        watermark_file_id: the watermark file ID

    Returns:
        None
    """
    if WATERMARK_ID not in user_data:
        return ConversationHandler.END

    source_file_id = user_data[WATERMARK_ID]
    update.message.reply_text('Adding the watermark onto your PDF file')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Watermarked_', suffix='.pdf'))
    source_file_name, watermark_file_name, out_file_name = [x.name for x in temp_files]

    # Download PDF files
    source_file = bot.get_file(source_file_id)
    source_file.download(custom_path=source_file_name)
    watermark_file = bot.get_file(watermark_file_id)
    watermark_file.download(custom_path=watermark_file_name)

    source_reader = open_pdf(source_file_name, update, 'source')
    if source_reader is not None:
        watermark_reader = open_pdf(watermark_file_name, update, 'watermark')
        if watermark_reader is not None:
            # Add watermark
            pdf_writer = PdfFileWriter()
            for page in source_reader.pages:
                page.mergePage(watermark_reader.getPage(0))
                pdf_writer.addPage(page)

            with open(out_file_name, 'wb') as f:
                pdf_writer.write(f)

            send_result(update, out_file_name, 'watermarked')

    # Clean up memory and files
    if user_data[WATERMARK_ID] == source_file_id:
        del user_data[WATERMARK_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END