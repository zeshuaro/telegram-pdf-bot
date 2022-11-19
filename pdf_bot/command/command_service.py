from telegram import ParseMode, Update
from telegram.chataction import ChatAction
from telegram.ext import CallbackContext

from pdf_bot.account.account_service import AccountService
from pdf_bot.language_new import LanguageService


class CommandService:
    def __init__(
        self, account_service: AccountService, language_service: LanguageService
    ) -> None:
        self.account_service = account_service
        self.language_service = language_service

    def send_start_message(self, update: Update, context: CallbackContext) -> None:
        update.effective_message.reply_chat_action(ChatAction.TYPING)

        # Create the user entity in Datastore
        self.account_service.create_user(update.effective_message.from_user)

        _ = self.language_service.set_app_language(update, context)
        update.effective_message.reply_text(
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
