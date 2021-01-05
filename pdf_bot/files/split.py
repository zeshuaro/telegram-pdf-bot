import tempfile

from pdf_bot.constants import PDF_INFO, WAIT_SPLIT_RANGE
from pdf_bot.files.utils import check_back_user_data, get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.utils import open_pdf, write_send_pdf
from PyPDF2 import PdfFileMerger
from PyPDF2.pagerange import PageRange
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram.parsemode import ParseMode


def ask_split_range(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    text = (
        "{intro}\n\n"
        "<b>{general}</b>\n"
        "<code>:      {all}</code>\n"
        "<code>7      {eight_only}</code>\n"
        "<code>0:3    {first_three}</code>\n"
        "<code>:3     {first_three}</code>\n"
        "<code>7:     {from_eight}</code>\n"
        "<code>-1     {last_only}</code>\n"
        "<code>:-1    {all_except_last}</code>\n"
        "<code>-2     {second_last}</code>\n"
        "<code>-2:    {last_two}</code>\n"
        "<code>-3:-1  {third_second}</code>\n\n"
        "<b>{advanced}</b>\n"
        "<code>::2    {pages} 0 2 4 ... {to_end}</code>\n"
        "<code>1:10:2 {pages} 1 3 5 7 9</code>\n"
        "<code>::-1   {all_reversed}</code>\n"
        "<code>3:0:-1 {pages} 3 2 1 {except_txt} 0</code>\n"
        "<code>2::-1  {pages} 2 1 0</code>"
    ).format(
        intro=_("Send me the range of pages that you'll like to keep"),
        general=_("General usage"),
        all=_("all pages"),
        eight_only=_("page 8 only"),
        first_three=_("first three pages"),
        from_eight=_("from page 8 onward"),
        last_only=_("last page only"),
        all_except_last=_("all pages except the last page"),
        second_last=_("second last page only"),
        last_two=_("last two pages"),
        third_second=_("third and second last pages"),
        advanced=_("Advanced usage"),
        pages=_("pages"),
        to_end=_("to the end"),
        all_reversed=_("all pages in reversed order"),
        except_txt=_("except"),
    )
    update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_markup(update, context),
    )

    return WAIT_SPLIT_RANGE


def split_pdf(update: Update, context: CallbackContext) -> int:
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    message = update.effective_message
    split_range = message.text

    if not PageRange.valid(split_range):
        message.reply_text(
            _(
                "The range is invalid. Try again",
                reply_markup=get_back_markup(update, context),
            )
        )

        return WAIT_SPLIT_RANGE

    message.reply_text(_("Splitting your PDF file"), reply_markup=ReplyKeyboardRemove())

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_reader = open_pdf(update, context, file_id, tf.name)

        if pdf_reader is not None:
            merger = PdfFileMerger()
            merger.append(pdf_reader, pages=PageRange(split_range))
            write_send_pdf(update, context, merger, file_name, "split")

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
