import tempfile

from PyPDF2 import PdfFileWriter
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import PDF_INVALID_FORMAT, PDF_OK
from pdf_bot.utils import cancel_with_async, check_pdf, open_pdf, write_send_pdf, check_user_data
from pdf_bot.language import set_lang

WAIT_WATERMARK_SOURCE = 0
WAIT_WATERMARK = 1
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
            WAIT_WATERMARK_SOURCE: [MessageHandler(Filters.document, receive_source_doc)],
            WAIT_WATERMARK: [MessageHandler(Filters.document, receive_watermark_doc)]
        },
        fallbacks=[CommandHandler('cancel', cancel_with_async)],
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
    _ = set_lang(update, context)
    update.effective_message.reply_text(_(
        'Send me the PDF file that you\'ll like to add a watermark or /cancel this action.'))

    return WAIT_WATERMARK_SOURCE


@run_async
def receive_source_doc(update, context):
    """
    Validate the file and wait for the watermark file
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the watermark file or the conversation has ended
    """
    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WATERMARK_SOURCE
    elif result != PDF_OK:
        return ConversationHandler.END

    _ = set_lang(update, context)
    context.user_data[WATERMARK_ID] = update.effective_message.document.file_id
    update.effective_message.reply_text(_('Send me the watermark PDF file'))

    return WAIT_WATERMARK


# Receive and check for the watermark PDF file and watermark the PDF file
@run_async
def receive_watermark_doc(update, context):
    """
    Validate the file and add the watermark onto the source PDF file
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the watermark file or the conversation has ended
    """
    if not check_user_data(update, context, WATERMARK_ID):
        return ConversationHandler.END

    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WATERMARK
    elif result != PDF_OK:
        return ConversationHandler.END

    return add_pdf_watermark(update, context)


def add_pdf_watermark(update, context):
    """
    Add watermark onto the PDF file
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    user_data = context.user_data
    if not check_user_data(update, context, WATERMARK_ID):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Adding the watermark onto your PDF file'))

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    source_fn, watermark_fn = [x.name for x in temp_files]

    # Download PDF files
    source_file_id = user_data[WATERMARK_ID]
    source_file = context.bot.get_file(source_file_id)
    source_file.download(custom_path=source_fn)
    watermark_file = context.bot.get_file(update.effective_message.document.file_id)
    watermark_file.download(custom_path=watermark_fn)

    source_reader = open_pdf(update, context, source_fn, 'source')
    if source_reader is not None:
        watermark_reader = open_pdf(update, context, watermark_fn, 'watermark')
        if watermark_reader is not None:
            # Add watermark
            pdf_writer = PdfFileWriter()
            for page in source_reader.pages:
                page.mergePage(watermark_reader.getPage(0))
                pdf_writer.addPage(page)

            # Send result file
            write_send_pdf(update, context, pdf_writer, 'file.pdf', 'watermarked')

    # Clean up memory and files
    if user_data[WATERMARK_ID] == source_file_id:
        del user_data[WATERMARK_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
