from telegram import (
    Message,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BEAUTIFY, CANCEL, REMOVE_LAST, TEXT_FILTER, TO_PDF
from pdf_bot.image import ImageService
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError


class BatchImageHandler:
    WAIT_IMAGE = 0
    IMAGE_DATA = "image_data"

    def __init__(
        self,
        image_service: ImageService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.image_service = image_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler("image", self.ask_first_image)],
            states={
                self.WAIT_IMAGE: [
                    MessageHandler(Filters.document | Filters.photo, self.check_image),
                    MessageHandler(TEXT_FILTER, self.check_text),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation)
            ],
            allow_reentry=True,
            run_async=True,
        )

    def ask_first_image(self, update: Update, context: CallbackContext) -> int:
        context.user_data[self.IMAGE_DATA] = []  # type: ignore
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_cancel_markup(
            update,
            context,
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_(
                    "Send me the images that you'll like to beautify or convert into a"
                    " PDF file"
                ),
                desc_2=_(
                    "Note that the images will be beautified and converted in the order"
                    " that you send me"
                ),
            ),
        )

        return self.WAIT_IMAGE

    def check_image(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore

        try:
            image = self.telegram_service.check_image(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return self.WAIT_IMAGE

        file_data = FileData.from_telegram_object(image)
        context.user_data[self.IMAGE_DATA].append(file_data)  # type: ignore
        return self._ask_next_image(update, context)

    def check_text(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        text = message.text

        if text in [_(REMOVE_LAST), _(BEAUTIFY), _(TO_PDF)]:
            try:
                file_data_list = self.telegram_service.get_user_data(
                    context, self.IMAGE_DATA
                )
            except TelegramServiceError as e:
                message.reply_text(_(str(e)))
                return ConversationHandler.END

            if text == _(REMOVE_LAST):
                return self._remove_last_image(update, context, file_data_list)
            return self._preprocess_images(update, context, file_data_list)
        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)
        return self.WAIT_IMAGE

    def _ask_next_image(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        text = "{desc}\n".format(desc=_("You've sent me these images so far:"))
        self.telegram_service.send_file_names(
            update.effective_chat.id, text, context.user_data[self.IMAGE_DATA]  # type: ignore
        )

        reply_markup = ReplyKeyboardMarkup(
            [[_(BEAUTIFY), _(TO_PDF)], [_(REMOVE_LAST), _(CANCEL)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        update.effective_message.reply_text(  # type: ignore
            _(
                "Select the task from below if you've sent me all the images, or keep"
                " sending me the images"
            ),
            reply_markup=reply_markup,
        )

        return self.WAIT_IMAGE

    def _remove_last_image(
        self, update: Update, context: CallbackContext, file_data_list: list[FileData]
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        try:
            file_data = file_data_list.pop()
        except IndexError:
            update.effective_message.reply_text(  # type: ignore
                _("You've already removed all the images you've sent me")
            )
            return self.ask_first_image(update, context)

        update.effective_message.reply_text(  # type: ignore
            _("{file_name} has been removed").format(
                file_name=f"<b>{file_data.file_name}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )

        if file_data_list:
            context.user_data[self.IMAGE_DATA] = file_data_list  # type: ignore
            return self._ask_next_image(update, context)
        return self.ask_first_image(update, context)

    def _preprocess_images(
        self, update: Update, context: CallbackContext, file_data_list: list[FileData]
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        num_files = len(file_data_list)

        if num_files == 0:
            update.effective_message.reply_text(_("You haven't sent me any images"))  # type: ignore
            return self.ask_first_image(update, context)
        if num_files == 1:
            update.effective_message.reply_text(_("You've only sent me one image"))  # type: ignore
            context.user_data[self.IMAGE_DATA] = file_data_list  # type: ignore
            return self._ask_next_image(update, context)
        return self._process_images(update, context, file_data_list)

    def _process_images(
        self, update: Update, context: CallbackContext, file_data_list: list[FileData]
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        is_beautify = False

        if message.text == _(BEAUTIFY):
            is_beautify = True
            text = _("Beautifying and converting your images into a PDF file")
        else:
            text = _("Converting your images into a PDF file")
        message.reply_text(text, reply_markup=ReplyKeyboardRemove())

        if is_beautify:
            with self.image_service.beautify_and_convert_images_to_pdf(
                file_data_list
            ) as out_path:
                self.telegram_service.send_file(
                    update, context, out_path, TaskType.beautify_image
                )
        else:
            with self.image_service.convert_images_to_pdf(file_data_list) as out_path:
                self.telegram_service.send_file(
                    update, context, out_path, TaskType.image_to_pdf
                )

        return ConversationHandler.END
