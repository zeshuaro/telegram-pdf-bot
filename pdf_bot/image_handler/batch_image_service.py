from gettext import gettext as _

from telegram import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import CANCEL
from pdf_bot.image import ImageService
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError


class BatchImageService:
    WAIT_IMAGE = 0
    IMAGE_DATA = "image_data"

    _BEAUTIFY = _("Beautify")
    _TO_PDF = _("To PDF")
    _REMOVE_LAST = _("Remove last file")

    def __init__(
        self,
        image_service: ImageService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.image_service = image_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    async def ask_first_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        context.user_data[self.IMAGE_DATA] = []  # type: ignore
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_cancel_markup(
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

    async def check_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore

        try:
            image = self.telegram_service.check_image(message)
        except TelegramServiceError as e:
            await message.reply_text(_(str(e)))
            return self.WAIT_IMAGE

        file_data = FileData.from_telegram_object(image)
        context.user_data[self.IMAGE_DATA].append(file_data)  # type: ignore
        return await self._ask_next_image(update, context)

    async def check_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        text = message.text

        if text in [_(self._REMOVE_LAST), _(self._BEAUTIFY), _(self._TO_PDF)]:
            try:
                file_data_list = self.telegram_service.get_user_data(
                    context, self.IMAGE_DATA
                )
            except TelegramServiceError as e:
                await message.reply_text(_(str(e)))
                return ConversationHandler.END

            if text == _(self._REMOVE_LAST):
                return await self._remove_last_image(update, context, file_data_list)
            return await self._preprocess_images(update, context, file_data_list)
        if text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)
        return self.WAIT_IMAGE

    async def _ask_next_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        text = "{desc}\n".format(desc=_("You've sent me these images so far:"))
        await self.telegram_service.send_file_names(
            update.effective_chat.id, text, context.user_data[self.IMAGE_DATA]  # type: ignore
        )

        reply_markup = ReplyKeyboardMarkup(
            [[_(self._BEAUTIFY), _(self._TO_PDF)], [_(self._REMOVE_LAST), _(CANCEL)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await update.effective_message.reply_text(  # type: ignore
            _(
                "Select the task from below if you've sent me all the images, or keep"
                " sending me the images"
            ),
            reply_markup=reply_markup,
        )

        return self.WAIT_IMAGE

    async def _remove_last_image(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_data_list: list[FileData],
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        try:
            file_data = file_data_list.pop()
        except IndexError:
            await update.effective_message.reply_text(  # type: ignore
                _("You've already removed all the images you've sent me")
            )
            return await self.ask_first_image(update, context)

        await update.effective_message.reply_text(  # type: ignore
            _("{file_name} has been removed").format(
                file_name=f"<b>{file_data.name}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )

        if file_data_list:
            context.user_data[self.IMAGE_DATA] = file_data_list  # type: ignore
            return await self._ask_next_image(update, context)
        return await self.ask_first_image(update, context)

    async def _preprocess_images(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_data_list: list[FileData],
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        num_files = len(file_data_list)

        if num_files == 0:
            await update.effective_message.reply_text(  # type: ignore
                _("You haven't sent me any images")
            )
            return await self.ask_first_image(update, context)
        if num_files == 1:
            await update.effective_message.reply_text(  # type: ignore
                _("You've only sent me one image")
            )
            context.user_data[self.IMAGE_DATA] = file_data_list  # type: ignore
            return await self._ask_next_image(update, context)
        return await self._process_images(update, context, file_data_list)

    async def _process_images(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_data_list: list[FileData],
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        is_beautify = False

        if message.text == _(self._BEAUTIFY):
            is_beautify = True
            text = _("Beautifying and converting your images into a PDF file")
        else:
            text = _("Converting your images into a PDF file")
        await message.reply_text(text, reply_markup=ReplyKeyboardRemove())

        if is_beautify:
            async with self.image_service.beautify_and_convert_images_to_pdf(
                file_data_list
            ) as out_path:
                await self.telegram_service.send_file(
                    update, context, out_path, TaskType.beautify_image
                )
        else:
            async with self.image_service.convert_images_to_pdf(
                file_data_list
            ) as out_path:
                await self.telegram_service.send_file(
                    update, context, out_path, TaskType.image_to_pdf
                )

        return ConversationHandler.END
