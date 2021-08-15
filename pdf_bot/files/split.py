import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.pagerange import PageRange
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram.parsemode import ParseMode

from pdf_bot.constants import PDF_INFO, WAIT_SPLIT_RANGE
from pdf_bot.files.utils import check_back_user_data, get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.utils import open_pdf, write_send_pdf


def ask_split_range(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    # "{intro}\n\n"
    # "<b>{general}</b>\n"
    # "<code>:      {all}</code>\n"
    # "<code>7      {eight_only}</code>\n"
    # "<code>0:3    {first_three}</code>\n"
    # "<code>7:     {from_eight}</code>\n"
    # "<code>-1     {last_only}</code>\n"
    # "<code>:-1    {all_except_last}</code>\n"
    # "<code>-2     {second_last}</code>\n"
    # "<code>-2:    {last_two}</code>\n"
    # "<code>-3:-1  {third_second}</code>\n\n"
    # "<b>{advanced}</b>\n"
    # "<code>::2    {pages} 0 2 4 ... {to_end}</code>\n"
    # "<code>1:10:2 {pages} 1 3 5 7 9</code>\n"
    # "<code>::-1   {all_reversed}</code>\n"
    # "<code>3:0:-1 {pages} 3 2 1 {except_txt} 0</code>\n"
    # "<code>2::-1  {pages} 2 1 0</code>"
    text = (
        "{intro}\n\n"
        "<b>{general}</b>\n"
        "<code>{all}</code>\n"
        "<code>{eight_only}</code>\n"
        "<code>{first_three}</code>\n"
        "<code>{from_eight}</code>\n"
        "<code>{last_only}</code>\n"
        "<code>{all_except_last}</code>\n"
        "<code>{second_last}</code>\n"
        "<code>{last_two}</code>\n"
        "<code>{third_second}</code>\n\n"
        "<b>{advanced}</b>\n"
        "<code>{pages_to_end}</code>\n"
        "<code>{odd_pages}</code>\n"
        "<code>{all_reversed}</code>\n"
        "<code>{pages_except}</code>\n"
        "<code>{pages_reverse_from}</code>"
    ).format(
        intro=_("Send me the range of pages that you'll like to keep"),
        general=_("General usage"),
        all=_("{range}      all pages").format(range=":"),
        eight_only=_("{range}      page 8 only").format(range="7"),
        first_three=_("{range}    first three pages").format(range="0:3"),
        from_eight=_("{range}     from page 8 onward").format(range="7:"),
        last_only=_("{range}     last page only").format(range="-1"),
        all_except_last=_("{range}    all pages except the last page").format(
            range=":-1"
        ),
        second_last=_("{range}     second last page only").format(range="-2"),
        last_two=_("{range}    last two pages").format(range="-2:"),
        third_second=_("{range}  third and second last pages").format(range="-3:-1"),
        advanced=_("Advanced usage"),
        pages_to_end=_("{range}    pages {pages} and to the end").format(
            range="::2", pages="0 2 4 ..."
        ),
        odd_pages=_("{range} pages {pages}").format(range="1:10:2", pages="1 3 5 7 9"),
        all_reversed=_("{range}   all pages in reversed order").format(range="::-1"),
        pages_except=_("{range} pages {pages} except {page}").format(
            range="3:0:-1", pages="3 2 1", page="0"
        ),
        pages_reverse_from=_("{range}  pages {pages}").format(
            range="2::-1", pages="2 1 0"
        ),
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
            _("The range is invalid, please try again"),
            reply_markup=get_back_markup(update, context),
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
