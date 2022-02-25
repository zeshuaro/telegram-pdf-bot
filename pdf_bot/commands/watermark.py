import tempfile

from PyPDF2 import PdfFileWriter
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL, PDF_INVALID_FORMAT, PDF_OK, TEXT_FILTER
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel, check_pdf, check_user_data, open_pdf, write_send_pdf

WAIT_SRC = 0
WAIT_WMK = 1
WMK_ID = "watermark_id"


def watermark_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("watermark", watermark)],
        states={
            WAIT_SRC: [MessageHandler(Filters.document, check_src_doc)],
            WAIT_WMK: [MessageHandler(Filters.document, check_wmk_doc)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(TEXT_FILTER, check_text),
        ],
        allow_reentry=True,
    )

    return conv_handler


def watermark(update, context):
    return ask_src_doc(update, context)


def ask_src_doc(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Send me the PDF file that you'll like to add a watermark"),
        reply_markup=reply_markup,
    )

    return WAIT_SRC


def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(BACK):
        return ask_src_doc(update, context)
    if text == _(CANCEL):
        return cancel(update, context)

    return None


def check_src_doc(update, context):
    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_SRC
    if result != PDF_OK:
        return ConversationHandler.END

    _ = set_lang(update, context)
    context.user_data[WMK_ID] = update.effective_message.document.file_id

    reply_markup = ReplyKeyboardMarkup(
        [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Send me the watermark PDF file"), reply_markup=reply_markup
    )

    return WAIT_WMK


def check_wmk_doc(update, context):
    if not check_user_data(update, context, WMK_ID):
        return ConversationHandler.END

    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WMK
    if result != PDF_OK:
        return ConversationHandler.END

    return add_wmk(update, context)


def add_wmk(update, context):
    if not check_user_data(update, context, WMK_ID):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Adding the watermark onto your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    src_fn, wmk_fn = [x.name for x in temp_files]

    user_data = context.user_data
    src_file_id = user_data[WMK_ID]
    wmk_file_id = update.effective_message.document.file_id
    src_reader = open_pdf(update, context, src_file_id, src_fn)

    if src_reader is not None:
        wmk_reader = open_pdf(update, context, wmk_file_id, wmk_fn, _("watermark"))
        if wmk_reader is not None:
            # Add watermark
            pdf_writer = PdfFileWriter()
            for page in src_reader.pages:
                page.mergePage(wmk_reader.getPage(0))
                pdf_writer.addPage(page)

            # Send result file
            write_send_pdf(
                update, context, pdf_writer, "file.pdf", TaskType.watermark_pdf
            )

    # Clean up memory and files
    if user_data[WMK_ID] == src_file_id:
        del user_data[WMK_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
