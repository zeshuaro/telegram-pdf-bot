from telegram import ParseMode, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.files.utils import get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.split import split_constants
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class SplitService:
    def __init__(
        self,
        file_task_service: FileTaskService,
        pdf_service: PdfService,
        telegram_service: TelegramService,
    ) -> None:
        self.file_task_service = file_task_service
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_split_range(update: Update, context: CallbackContext):
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
            third_second=_("{range}  third and second last pages").format(
                range="-3:-1"
            ),
            advanced=_("Advanced usage"),
            pages_to_end=_("{range}    pages {pages} and to the end").format(
                range="::2", pages="0 2 4 ..."
            ),
            odd_pages=_("{range} pages {pages}").format(
                range="1:10:2", pages="1 3 5 7 9"
            ),
            all_reversed=_("{range}   all pages in reversed order").format(
                range="::-1"
            ),
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

        return split_constants.WAIT_SPLIT_RANGE

    def split_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        split_range = message.text
        if not self.pdf_service.split_range_valid(split_range):
            message.reply_text(
                _("The range is invalid, please try again"),
                reply_markup=get_back_markup(update, context),
            )
            return split_constants.WAIT_SPLIT_RANGE

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.split_pdf(file_id, split_range) as out_path:
            send_result_file(update, context, out_path, TaskType.split_pdf)

        return ConversationHandler.END
