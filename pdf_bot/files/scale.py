from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from pdf_bot.constants import (
    BACK,
    BY_PERCENT,
    TO_DIMENSIONS,
    WAIT_SCALE_DIMENSION,
    WAIT_SCALE_PERCENT,
    WAIT_SCALE_TYPE,
)
from pdf_bot.files.utils import get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.utils import process_pdf


def ask_scale_type(update, context):
    _ = set_lang(update, context)
    keyboard = [[_(BY_PERCENT), _(TO_DIMENSIONS)], [_(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the scale type that you'll like to perform"),
        reply_markup=reply_markup,
    )

    return WAIT_SCALE_TYPE


def ask_scale_value(update, context, ask_percent=True):
    _ = set_lang(update, context)
    message = update.effective_message
    reply_markup = get_back_markup(update, context)

    if message.text == _(TO_DIMENSIONS) or not ask_percent:
        message.reply_text(
            "{desc_1}\n{desc_2}\n\n{desc_3}".format(
                desc_1=_("Send me the width and height"),
                desc_2="<b>{}</b>".format(_("Example: 150 200")),
                desc_3=_("This will set the width to 150 and height to 200"),
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

        return WAIT_SCALE_DIMENSION
    else:
        message.reply_text(
            "{desc_1}\n{desc_2}\n\n{desc_3}".format(
                desc_1=_(
                    "Send me the scaling factors for the horizontal and vertical axes"
                ),
                desc_2="<b>{}</b>".format(_("Example: 2 0.5")),
                desc_3=_(
                    "This will double the horizontal axis and halve the vertical axis"
                ),
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

        return WAIT_SCALE_PERCENT


def check_scale_percent(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    text = message.text

    if text == _(BACK):
        return ask_scale_type(update, context)

    try:
        x, y = map(float, text.split())
    except ValueError:
        message.reply_text(
            _("The scaling factors {} are invalid, please try again").format(
                "<b>{}</b>".format(text)
            ),
            parse_mode=ParseMode.HTML,
        )
        return ask_scale_value(update, context)

    return scale_pdf(update, context, percent=(x, y))


def check_scale_dimension(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    text = message.text

    if text == _(BACK):
        return ask_scale_type(update, context)

    try:
        x, y = map(float, text.split())
    except ValueError:
        message.reply_text(
            _("The dimensions {} are invalid, please try again").format(
                "<b>{}</b>".format(text)
            ),
            parse_mode=ParseMode.HTML,
        )
        return ask_scale_value(update, context, ask_percent=False)

    return scale_pdf(update, context, dim=(x, y))


def scale_pdf(update, context, percent=None, dim=None):
    _ = set_lang(update, context)
    if percent is not None:
        update.effective_message.reply_text(
            _(
                "Scaling your PDF file, horizontally by {horizontal} "
                "and vertically by {vertical}"
            ).format(
                horizontal="<b>{}</b>".format(percent[0]),
                vertical="<b>{}</b>".format(percent[1]),
            ),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        process_pdf(update, context, "scaled", scale_by=percent)
    else:
        update.effective_message.reply_text(
            _(
                "Scaling your PDF file with width of {width} and height of {height}"
            ).format(
                width="<b>{}</b>".format(dim[0]), height="<b>{}</b>".format(dim[1])
            ),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        process_pdf(update, context, "scaled", scale_to=dim)

    return ConversationHandler.END
