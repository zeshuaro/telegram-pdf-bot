from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from pdf_bot.account.account_service import AccountService
from pdf_bot.consts import CHANNEL_NAME, PAYMENT, SET_LANG
from pdf_bot.language import LanguageService


class CommandService:
    def __init__(
        self, account_service: AccountService, language_service: LanguageService
    ) -> None:
        self.account_service = account_service
        self.language_service = language_service

    async def send_start_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await update.message.reply_chat_action(ChatAction.TYPING)

        # Create the user entity in Datastore
        self.account_service.create_user(update.message.from_user)

        _ = self.language_service.set_app_language(update, context)
        await update.message.reply_text(
            "{welcome}\n\n<b>{key_features}</b>\n"
            "{features_summary}\n"
            "{pdf_from_text}\n"
            "{extract_pdf}\n"
            "{convert_to_images}\n"
            "{convert_to_pdf}\n"
            "{beautify}\n"
            "<b><i>{and_more}</i></b>\n\n"
            "{see_usage}".format(
                welcome=_("Welcome to PDF Bot!"),
                key_features=_("Key features:"),
                features_summary=_(
                    "- Compress, merge, preview, rename, split "
                    "and add watermark to PDF files"
                ),
                pdf_from_text=_("- Create PDF files from text messages"),
                extract_pdf=_("- Extract images and text from PDF files"),
                convert_to_images=_("- Convert PDF files into images"),
                convert_to_pdf=_("- Convert webpages and images into PDF files"),
                beautify=_("- Beautify handwritten notes images into PDF files"),
                and_more=_("- And more..."),
                see_usage=_("Type {command} to see how to use PDF Bot").format(
                    command="/help"
                ),
            ),
            parse_mode=ParseMode.HTML,
        )

    async def send_help_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [InlineKeyboardButton(_("Set Language 🌎"), callback_data=SET_LANG)],
            [
                InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
                InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "{desc_1}\n{pdf_files}\n{images}\n{webpage_links}\n\n{desc_2}\n"
            "{compare_desc}\n{merge_desc}\n{image_desc}\n{text_desc}\n"
            "{watermark_desc}".format(
                desc_1=_(
                    "You can perform most of the tasks by sending me one of the"
                    " followings:"
                ),
                pdf_files=_("- PDF files"),
                images=_("- Images"),
                webpage_links=_("- Webpage links"),
                desc_2=_(
                    "The rest of the tasks can be performed by using the following "
                    "commands:"
                ),
                compare_desc=_("{command} - compare PDF files").format(
                    command="/compare"
                ),
                merge_desc=_("{command} - merge PDF files").format(command="/merge"),
                image_desc=_(
                    "{command} - convert and combine multiple images into PDF files"
                ).format(command="/image"),
                text_desc=_("{command} - create PDF files from text messages").format(
                    command="/text"
                ),
                watermark_desc=_("{command} - add watermark to PDF files").format(
                    command="/watermark"
                ),
            ),
            reply_markup=reply_markup,
        )

    async def send_message_to_user(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        args = context.args
        if args is not None:
            user_id = int(args[0])
            message = " ".join(args[1:])

            try:
                await context.bot.send_message(user_id, message)
                await update.message.reply_text("Message sent")
            except Forbidden:
                await update.message.reply_text("User has blocked the bot")
        else:
            await update.message.reply_text(f"Invalid arguments: {args}")
