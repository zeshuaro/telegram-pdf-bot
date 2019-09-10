import tempfile

from PyPDF2 import PdfFileWriter
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import PDF_INVALID_FORMAT, PDF_OK, CANCEL, BACK
from pdf_bot.utils import cancel_with_async, check_pdf, open_pdf, write_send_pdf, check_user_data, \
    cancel_without_async
from pdf_bot.language import set_lang

WAIT_SRC = 0
WAIT_WMK = 1
WMK_ID = 'watermark_id'


def watermark_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('watermark', watermark)],
        states={
            WAIT_SRC: [MessageHandler(Filters.document, check_src_doc)],
            WAIT_WMK: [MessageHandler(Filters.document, check_wmk_doc)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_with_async),
            MessageHandler(Filters.text, check_text)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def watermark(update, context):
    return ask_src_doc(update, context)


def ask_src_doc(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup([[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the PDF file that you\'ll like to add a watermark'), reply_markup=reply_markup)

    return WAIT_SRC


@run_async
def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(BACK):
        return ask_src_doc(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


@run_async
def check_src_doc(update, context):
    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_SRC
    elif result != PDF_OK:
        return ConversationHandler.END

    _ = set_lang(update, context)
    context.user_data[WMK_ID] = update.effective_message.document.file_id

    reply_markup = ReplyKeyboardMarkup(
        [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the watermark PDF file'), reply_markup=reply_markup)

    return WAIT_WMK


@run_async
def check_wmk_doc(update, context):
    if not check_user_data(update, context, WMK_ID):
        return ConversationHandler.END

    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WMK
    elif result != PDF_OK:
        return ConversationHandler.END

    return add_wmk(update, context)


def add_wmk(update, context):
    if not check_user_data(update, context, WMK_ID):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(_(
        'Adding the watermark onto your PDF file'), reply_markup=ReplyKeyboardRemove())

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    src_fn, wmk_fn = [x.name for x in temp_files]

    user_data = context.user_data
    src_file_id = user_data[WMK_ID]
    wmk_file_id = update.effective_message.document.file_id
    src_reader = open_pdf(update, context, src_file_id, src_fn, 'source')

    if src_reader is not None:
        wmk_reader = open_pdf(update, context, wmk_file_id, wmk_fn, 'watermark')
        if wmk_reader is not None:
            # Add watermark
            pdf_writer = PdfFileWriter()
            for page in src_reader.pages:
                page.mergePage(wmk_reader.getPage(0))
                pdf_writer.addPage(page)

            # Send result file
            write_send_pdf(update, context, pdf_writer, 'file.pdf', 'watermarked')

    # Clean up memory and files
    if user_data[WMK_ID] == src_file_id:
        del user_data[WMK_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
