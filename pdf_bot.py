#!/usr/bin/env python3
# coding: utf-8

import dotenv
import logging
import os
import requests
import shlex
import shutil
import tempfile
import wand.image

from feedback_bot import feedback_cov_handler
from PIL import Image as PillowImage
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.utils import PdfReadError
from subprocess import Popen, PIPE

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction
from telegram.constants import *
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, RegexHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot_globals import *

# Enable logging
logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %I:%M:%S %p',
                    level=logging.INFO)
LOGGER = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
dotenv.load_dotenv(dotenv_path)
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get("PORT", "5000"))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN_BETA", os.environ.get("TELEGRAM_TOKEN"))
DEV_TELE_ID = int(os.environ.get("DEV_TELE_ID"))
DEV_EMAIL = os.environ.get("DEV_EMAIL", "sample@email.com")
converter_url = os.environ.get("CONVERTER_URL", ) if os.environ.get("CONVERTER_URL") else \
    "https://github.com/yeokm1/docs-to-pdf-converter/releases/download/v1.8/docs-to-pdf-converter-1.8.jar"

CHANNEL_NAME = "pdf2botdev"  # Channel username
BOT_NAME = "pdf2bot"  # Bot username


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN, request_kwargs={"connect_timeout": 20, "read_timeout": 20})

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start_msg))
    dp.add_handler(CommandHandler("help", help_msg))
    dp.add_handler(CommandHandler("donate", donate_msg))
    dp.add_handler(compare_cov_handler())
    dp.add_handler(merge_cov_handler())
    dp.add_handler(watermark_cov_handler())
    dp.add_handler(pdf_cov_handler())
    dp.add_handler(feedback_cov_handler())
    dp.add_handler(CommandHandler("send", send, pass_args=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if APP_URL:
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TELEGRAM_TOKEN)
        updater.bot.set_webhook(APP_URL + TELEGRAM_TOKEN)
    else:
        updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


# Send start message
@run_async
def start_msg(bot, update):
    text = "Welcome to PDF Bot!\n\n"
    text += "I can compare, decrypt, encrypt, merge, rotate, scale, split and add watermark to a PDF file.\n\n "
    # text += "I can also convert doc, docx, ppt, pptx and odt files into PDF format and convert a PDF file into " \
    #         "images.\n\n"
    text += "I can also extract images in a PDF file and convert a PDF file into images.\n\n"
    text += "Type /help to see how to use me."

    update.message.reply_text(text)


# Send help message
@run_async
def help_msg(bot, update):
    text = "You can perform most of the tasks simply by sending me a PDF file. You can then select a task and I " \
           "will guide you through each of the tasks.\n\n"
    text += "If you want to compare, merge or add watermark to PDF files, you will have to use the /compare, " \
            "/merge or /watermark commands respectively.\n\n"
    # text += "If you want to convert a file into PDF format, simply send me one of the supported formats and I'll " \
    #         "convert it for you.\n\n"
    text += "Please note that I can only download files up to 20 MB in size and upload files up to 50 MB in size. " \
            "If the result files are too large, I will not be able to send you the file.\n\n"

    keyboard = [[InlineKeyboardButton("Join Channel", f"https://t.me/{CHANNEL_NAME}"),
                 InlineKeyboardButton("Rate me", f"https://t.me/storebot?start={BOT_NAME}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(text, reply_markup=reply_markup)


# Send donate message
@run_async
def donate_msg(bot, update):
    text = f"Want to help keep me online? Please donate to {DEV_EMAIL} through PayPal.\n\n" \
           f"Donations help me to stay on my server and keep running."

    update.message.reply_text(text)


# Create a compare conversation handler
def compare_cov_handler():
    merged_filter = Filters.document & (Filters.forwarded | ~Filters.forwarded)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compare", compare)],

        states={
            WAIT_FIRST_COMPARE_FILE: [MessageHandler(merged_filter, check_first_compare_file, pass_user_data=True)],
            WAIT_SECOND_COMPARE_FILE: [MessageHandler(merged_filter, check_second_compare_file, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Start the compare conversation
@run_async
def compare(bot, update):
    update.message.reply_text("Please send me one of the PDF files that you will like to compare or type /cancel to "
                              "cancel this operation\n\nPlease note that I can only look for text differences")

    return WAIT_FIRST_COMPARE_FILE


# Receive and check for the first PDF file
@run_async
def check_first_compare_file(bot, update, user_data):
    result = check_pdf(bot, update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_FIRST_COMPARE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    user_data["compare_file_id"] = update.message.document.file_id
    update.message.reply_text("Please send me the other PDF file that you will like to compare")

    return WAIT_SECOND_COMPARE_FILE


# Receive and check for the second PDF file
# If success, compare the two PDF files
@run_async
def check_second_compare_file(bot, update, user_data):
    if "compare_file_id" not in user_data:
        return ConversationHandler.END

    result = check_pdf(bot, update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_SECOND_COMPARE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    return compare_pdf(bot, update, user_data, update.message.document.file_id)


# Compare two PDF files
def compare_pdf(bot, update, user_data, second_file_id):
    if "compare_file_id" not in user_data:
        return ConversationHandler.END

    first_file_id = user_data["compare_file_id"]
    update.message.reply_text("Comparing your PDF files")

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix="Compared_", suffix=".png"))
    first_filename = temp_files[0].name
    second_filename = temp_files[1].name
    diff_filename = temp_files[2].name

    # Download PDF files
    first_pdf_file = bot.get_file(first_file_id)
    first_pdf_file.download(custom_path=first_filename)
    second_pdf_file = bot.get_file(second_file_id)
    second_pdf_file.download(custom_path=second_filename)

    # Run pdf-diff
    command = "pdf-diff {first_pdf} {second_pdf}".format(first_pdf=first_filename, second_pdf=second_filename)
    proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    proc_out, proc_err = proc.communicate()

    if proc.returncode != 0:
        if "there are no text difference" in proc_err.decode("utf8").strip().lower():
            update.message.reply_text("There are no differences between the two PDF files you sent me")
        else:
            LOGGER.error(proc_err.decode("utf8"))
            update.message.reply_text("Something went wrong, please try again")

        return ConversationHandler.END

    # Write diff results to file
    with open(diff_filename, "wb") as f:
        f.write(proc_out)

    # Send results back to user
    if os.path.getsize(diff_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The difference result file is too large for me to send to you, sorry")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(diff_filename, "rb"),
                                      caption="Here are the differences between your PDF files")

    # Clean up memory and files
    if user_data["compare_file_id"] == first_file_id:
        del user_data["compare_file_id"]

    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Creates a merge conversation handler
def merge_cov_handler():
    merged_filter = Filters.document & (Filters.forwarded | ~Filters.forwarded)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("merge", merge, pass_user_data=True)],

        states={
            WAIT_MERGE_FILE: [MessageHandler(merged_filter, receive_merge_file, pass_user_data=True),
                              RegexHandler("^Done$", merge_pdf, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the merge conversation
@run_async
def merge(bot, update, user_data):
    # Clears previous merge info
    if "merge_file_ids" in user_data:
        del user_data["merge_file_ids"]

    if "merge_filenames" in user_data:
        del user_data["merge_filenames"]

    update.message.reply_text("Please send me the first PDF file that you will like to merge or type /cancel to "
                              "cancel this operation.\n\nThe files will be merged in the order that you send me.")

    return WAIT_MERGE_FILE


# Receives and checks for the source PDF file
@run_async
def receive_merge_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name
    file_id = pdf_file.file_id
    file_size = pdf_file.file_size

    if not filename.endswith(".pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to merge or type /cancel to cancel this operation.")

        return WAIT_MERGE_FILE
    elif file_size >= MAX_FILESIZE_DOWNLOAD:
        text = "The PDF file you sent is too large for me to download.\n\n"

        if "merge_filenames" in user_data and user_data["merge_filenames"]:
            text += "You can continue merging with the files that you sent me or type /cancel to cancel this operation."
            update.message.reply_text(text)

            send_received_filenames(update, user_data["merge_filenames"])

            return WAIT_MERGE_FILE
        else:
            text += "Sorry that I can't merge your PDF files. Operation cancelled."
            update.message.reply_text(text)

            return ConversationHandler.END

    is_encrypted = is_pdf_encrypted(bot, file_id)
    if is_encrypted or is_encrypted is None:
        if is_encrypted is None:
            text = "Your PDF file is invalid and I couldn't read it. "
        else:
            text = "The PDF file you sent is encrypted. Please decrypt it yourself or use decrypt it with me first. "

        if "merge_filenames" in user_data and user_data["merge_filenames"]:
            text += "\n\nYou can continue merging with the files that you sent me or type /cancel to cancel this " \
                    "operation."
            update.message.reply_text(text)

            send_received_filenames(update, user_data["merge_filenames"])

            return WAIT_MERGE_FILE
        else:
            text += "Operation cancelled."
            update.message.reply_text(text)

            return ConversationHandler.END

    if "merge_file_ids" in user_data and user_data["merge_file_ids"]:
        user_data["merge_file_ids"].append(file_id)
        user_data["merge_filenames"].append(filename)
    else:
        user_data["merge_file_ids"] = [file_id]
        user_data["merge_filenames"] = [filename]

    keyboard = [["Done"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("Please send me the next PDF file that you will like to merge or say Done if you have "
                              "sent me all the PDF files that you want to merge.", reply_markup=reply_markup)

    send_received_filenames(update, user_data["merge_filenames"])

    return WAIT_MERGE_FILE


# Sends a list of received filenames
@run_async
def send_received_filenames(update, filenames):
    text = "You have sent me the following PDF files:\n"

    for i, filename in enumerate(filenames):
        text += "%d: %s\n" % ((i + 1), filename)

    update.message.reply_text(text)


# Merges PDF file
def merge_pdf(bot, update, user_data):
    if "merge_file_ids" not in user_data:
        return ConversationHandler.END

    file_ids = user_data["merge_file_ids"]
    filenames = user_data["merge_filenames"]
    update.message.reply_text("Merging your files.", reply_markup=ReplyKeyboardRemove())

    temp_files = [tempfile.NamedTemporaryFile() for _ in range(len(file_ids))]
    temp_files.append(tempfile.NamedTemporaryFile(prefix="Merged_", suffix=".pdf"))
    out_filename = temp_files[-1].name
    merger = PdfFileMerger()

    for i, file_id in enumerate(file_ids):
        filename = temp_files[i].name
        pdf_file = bot.get_file(file_id)
        pdf_file.download(custom_path=filename)
        merger.append(open(filename, "rb"))

    with open(out_filename, "wb") as f:
        merger.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The merged PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your merged PDF file.")

    if user_data["merge_file_ids"] == file_ids:
        del user_data["merge_file_ids"]
    if user_data["merge_filenames"] == filenames:
        del user_data["merge_filenames"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Creates a watermark conversation handler
def watermark_cov_handler():
    merged_filter = Filters.document & (Filters.forwarded | ~Filters.forwarded)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("watermark", watermark)],

        states={
            WAIT_WATERMARK_SOURCE_FILE: [MessageHandler(merged_filter, receive_watermark_source_file,
                                                        pass_user_data=True)],
            WAIT_WATERMARK_FILE: [MessageHandler(merged_filter, receive_watermark_file, pass_user_data=True)]
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the watermark conversation
@run_async
def watermark(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to add a watermark or type /cancel to "
                              "cancel this operation.")

    return WAIT_WATERMARK_SOURCE_FILE


# Receives and checks for the source PDF file
@run_async
def receive_watermark_source_file(bot, update, user_data):
    result = check_pdf(bot, update)

    if result == 1:
        return WAIT_WATERMARK_SOURCE_FILE
    elif result != 0:
        return ConversationHandler.END

    user_data["watermark_file_id"] = update.message.document.file_id
    update.message.reply_text("Please send me the watermark in PDF format.")

    return WAIT_WATERMARK_FILE


# Receives and checks for the watermark PDF file and watermark the PDF file
@run_async
def receive_watermark_file(bot, update, user_data):
    if "watermark_file_id" not in user_data:
        return ConversationHandler.END

    result = check_pdf(bot, update)

    if result == 1:
        return WAIT_WATERMARK_FILE
    elif result != 0:
        return ConversationHandler.END

    return add_pdf_watermark(bot, update, user_data, update.message.document.file_id)


# Adds watermark to PDF file
def add_pdf_watermark(bot, update, user_data, watermark_file_id):
    if "watermark_file_id" not in user_data:
        return ConversationHandler.END

    source_file_id = user_data["watermark_file_id"]
    update.message.reply_text("Adding the watermark to your PDF file.")

    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix="Watermarked_", suffix=".pdf"))
    source_filename = temp_files[0].name
    watermark_filename = temp_files[1].name
    out_filename = temp_files[2].name

    source_pdf_file = bot.get_file(source_file_id)
    source_pdf_file.download(custom_path=source_filename)

    watermark_pdf_file = bot.get_file(watermark_file_id)
    watermark_pdf_file.download(custom_path=watermark_filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(source_filename, "rb"))
    watermark_reader = PdfFileReader(open(watermark_filename, "rb"))

    for page in pdf_reader.pages:
        page.mergePage(watermark_reader.getPage(0))
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The watermarked PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your watermarked PDF file.")

    if user_data["watermark_file_id"] == source_file_id:
        del user_data["watermark_file_id"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Checks PDF files
def check_pdf(bot, update):
    update.message.chat.send_action(ChatAction.TYPING)

    pdf_status = PDF_OK
    pdf_file = update.message.document
    mime_type = pdf_file.mime_type
    file_id = pdf_file.file_id
    file_size = pdf_file.file_size

    if not mime_type.endswith("pdf"):
        pdf_status = PDF_INVALID_FORMAT
        update.message.reply_text("The file you sent is not a PDF file. Please try again and send me a PDF file or "
                                  "type /cancel to cancel the operation.")
    elif file_size >= MAX_FILESIZE_DOWNLOAD:
        pdf_status = PDF_TOO_LARGE
        update.message.reply_text("The PDF file you sent is too large for me to download. "
                                  "Sorry that I can't process your PDF file. Operation cancelled.")

    # is_encrypted = is_pdf_encrypted(bot, file_id)
    # if is_encrypted is None:
    #     pdf_status = 3
    #     update.message.reply_text("Your PDF file is invalid and I couldn't read it. Operation cancelled.")
    # elif is_encrypted:
    #     pdf_status = 3
    #     update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or decrypt it with "
    #                               "me first. Operation cancelled.")

    return pdf_status


# Creates a PDF conversation handler
def pdf_cov_handler():
    merged_filter = Filters.document & (Filters.forwarded | ~Filters.forwarded)

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(merged_filter, check_doc, pass_user_data=True)],

        states={
            WAIT_TASK: [RegexHandler("^Cover$", get_pdf_cover_img, pass_user_data=True),
                        RegexHandler("^Decrypt$", ask_decrypt_pw),
                        RegexHandler("^Encrypt$", ask_encrypt_pw),
                        RegexHandler("^Extract Images$", get_pdf_img, pass_user_data=True),
                        RegexHandler("^To Images$", pdf_to_img, pass_user_data=True),
                        RegexHandler("^Rotate$", ask_rotate_degree),
                        RegexHandler("^Scale By$", ask_scale_x),
                        RegexHandler("^Scale To$", ask_scale_x),
                        RegexHandler("^Split$", ask_split_range)],
            WAIT_DECRYPT_PW: [MessageHandler(Filters.text, decrypt_pdf, pass_user_data=True)],
            WAIT_ENCRYPT_PW: [MessageHandler(Filters.text, encrypt_pdf, pass_user_data=True)],
            WAIT_ROTATE_DEGREE: [RegexHandler("^(90|180|270)$", rotate_pdf, pass_user_data=True)],
            WAIT_SCALE_BY_X: [MessageHandler(Filters.text, ask_scale_by_y, pass_user_data=True)],
            WAIT_SCALE_BY_Y: [MessageHandler(Filters.text, pdf_scale_by, pass_user_data=True)],
            WAIT_SCALE_TO_X: [MessageHandler(Filters.text, ask_scale_to_y, pass_user_data=True)],
            WAIT_SCALE_TO_Y: [MessageHandler(Filters.text, pdf_scale_to, pass_user_data=True)],
            WAIT_SPLIT_RANGE: [MessageHandler(Filters.text, split_pdf, pass_user_data=True)]
        },

        fallbacks=[CommandHandler("cancel", cancel), RegexHandler("^Cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Checks if the document is a PDF file and if it exceeds the download size limit
@run_async
def check_doc(bot, update, user_data):
    update.message.chat.send_action(ChatAction.TYPING)

    doc = update.message.document
    file_mime_type = doc.mime_type
    file_id = doc.file_id
    file_size = doc.file_size
    # convert_mime_types = ("msword", "officedocument.wordprocessingml.document", "ms-powerpoint",
    #                       "officedocument.presentationml.presentation", "opendocument.text")

    # if file_mime_type.endswith(convert_mime_types):
    #     if file_size >= MAX_FILESIZE_DOWNLOAD:
    #         update.message.reply_text("The file you sent is too large for me to download. "
    #                                   "Sorry that I can't convert your file into PDF format.")
    #
    #         return ConversationHandler.END
    #
    #     return convert_to_pdf(bot, update, file_id, file_mime_type)
    if not file_mime_type.endswith("pdf"):
        return ConversationHandler.END
    elif file_mime_type.endswith("pdf") and file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text("The PDF file you sent is too large for me to download. "
                                  "Sorry that I can't perform any tasks on your PDF file.")

        return ConversationHandler.END

    is_encrypted = is_pdf_encrypted(bot, file_id)
    if is_encrypted is None:
        update.message.reply_text("Your PDF file is invalid and I couldn't read it.")

        return ConversationHandler.END
    elif is_encrypted:
        keywords = ["Decrypt"]
    else:
        keywords = sorted(["Encrypt", "Rotate", "Scale By", "Scale To", "Split", "Cover", "To Images",
                           "Extract Images"])

    user_data["pdf_id"] = file_id
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append(["Cancel"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Please select the task that you'll like to perform.",
                              reply_markup=reply_markup)

    return WAIT_TASK


# Converts a file into PDF format
@run_async
def convert_to_pdf(bot, update, file_id, file_mime_type):
    update.message.reply_text("Converting your file into PDF format.")

    temp_files = [tempfile.NamedTemporaryFile(prefix="Converted_", suffix=".pdf")]
    out_filename = temp_files[0].name

    if file_mime_type.endswith("word"):
        tf = tempfile.NamedTemporaryFile(suffix=".doc")
        filename = tf.name
    elif file_mime_type.endswith("document"):
        tf = tempfile.NamedTemporaryFile(suffix=".docx")
        filename = tf.name
    elif file_mime_type.endswith("powerpoint"):
        tf = tempfile.NamedTemporaryFile(suffix=".ppt")
        filename = tf.name
    elif file_mime_type.endswith("presentation"):
        tf = tempfile.NamedTemporaryFile(suffix=".pptx")
        filename = tf.name
    else:
        tf = tempfile.NamedTemporaryFile(suffix=".odt")
        filename = tf.name

    temp_files.append(tf)
    convert_file = bot.get_file(file_id)
    convert_file.download(custom_path=filename)
    download_converter()

    command = "java -jar doc-converter.jar -i {in_filename} -o {out_filename}". \
        format(out_filename=out_filename, in_filename=filename)

    process = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    process_out, process_err = process.communicate()

    if process.returncode != 0 or not os.path.exists(out_filename) or "[Errno" in process_err.decode("utf8").strip() \
            or os.path.getsize(out_filename) == 0:
        update.message.reply_text("Something went wrong. Please try again.")

        return ConversationHandler.END

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The converted PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your PDF file.")

    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Downloads converter
def download_converter():
    if not os.path.exists("doc-converter.jar"):
        r = requests.get(converter_url)

        with open("doc-converter.jar", "wb") as f:
            f.write(r.content)


# Checks if PDF file is encrypted
def is_pdf_encrypted(bot, file_id):
    tf = tempfile.NamedTemporaryFile()
    filename = tf.name
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    try:
        pdf_reader = PdfFileReader(open(filename, "rb"))
    except PdfReadError:
        tf.close()
        return None

    encrypted = pdf_reader.isEncrypted
    tf.close()

    return encrypted


# Gets the PDF cover in jpg format
@run_async
def get_pdf_cover_img(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    update.message.reply_text("Extracting a cover preview for your PDF file.", reply_markup=ReplyKeyboardRemove())

    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix="Cover_", suffix=".jpg"))
    filename = temp_files[0].name
    tmp_filename = temp_files[1].name
    out_filename = temp_files[2].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_reader = PdfFileReader(open(filename, "rb"))
    pdf_writer = PdfFileWriter()
    pdf_writer.addPage(pdf_reader.getPage(0))

    with open(tmp_filename, "wb") as f:
        pdf_writer.write(f)

    with wand.image.Image(filename=tmp_filename, resolution=300) as img:
        with img.convert("jpg") as converted:
            converted.save(filename=out_filename)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The cover preview is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        update.message.reply_photo(photo=open(out_filename, "rb"),
                                   caption="Here is the cover preview of your PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Asks user for decryption password
@run_async
def ask_decrypt_pw(bot, update):
    update.message.reply_text("Please send me the password to decrypt your PDF file.",
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_DECRYPT_PW


# Decrypts the PDF file with the given password
@run_async
def decrypt_pdf(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    pw = update.message.text
    update.message.reply_text("Decrypting your PDF file.")

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix="Decrypted_", suffix=".pdf")]
    filename = temp_files[0].name
    out_filename = temp_files[1].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    pdf_reader = PdfFileReader(open(filename, "rb"))

    try:
        if pdf_reader.decrypt(pw) == 0:
            update.message.reply_text("The decryption password is incorrect. Please send it again.")

            return WAIT_DECRYPT_PW
    except NotImplementedError:
        update.message.reply_text("The PDF file is encrypted with a method that I cannot decrypt. Sorry.")

        return ConversationHandler.END

    pdf_writer = PdfFileWriter()

    for page in pdf_reader.pages:
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The decrypted PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your decrypted PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Asks user for encryption password
@run_async
def ask_encrypt_pw(bot, update):
    update.message.reply_text("Please send me the password to encrypt your PDF file.",
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_ENCRYPT_PW


# Encrypts the PDF file with the given password
@run_async
def encrypt_pdf(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    pw = update.message.text
    update.message.reply_text("Encrypting your PDF file.")

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix="Encrypted_", suffix=".pdf")]
    filename = temp_files[0].name
    out_filename = temp_files[1].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        pdf_writer.addPage(page)

    pdf_writer.encrypt(pw)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The encrypted PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your encrypted PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Gets the images in the PDF file
@run_async
def get_pdf_img(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    update.message.reply_text("Extracting all the images in your PDF file.", reply_markup=ReplyKeyboardRemove())

    temp_dir = tempfile.TemporaryDirectory(prefix="Images_")
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    filename = tf.name
    out_filename = image_dir + ".zip"

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        if "/Resources" in page and "/XObject" in page["/Resources"]:
            xObject = page["/Resources"]["/XObject"].getObject()
    
            for obj in xObject:
                if xObject[obj]["/Subtype"] == "/Image":
                    size = (xObject[obj]["/Width"], xObject[obj]["/Height"])

                    try:
                        data = xObject[obj].getData()
                    except:
                        continue

                    if xObject[obj]["/ColorSpace"] == "/DeviceRGB":
                        mode = "RGB"
                    else:
                        mode = "P"
    
                    if xObject[obj]["/Filter"] == "/FlateDecode":
                        try:
                            img = PillowImage.frombytes(mode, size, data)
                            img.save(tempfile.NamedTemporaryFile(dir=image_dir, suffix=".png").name)
                        except TypeError:
                            pass
                    elif xObject[obj]["/Filter"] == "/DCTDecode":
                        with open(tempfile.NamedTemporaryFile(dir=image_dir, suffix=".jpg").name, "wb") as img:
                            img.write(data)
                    elif xObject[obj]["/Filter"] == "/JPXDecode":
                        with open(tempfile.NamedTemporaryFile(dir=image_dir, suffix=".jp2").name, "wb") as img:
                            img.write(data)

    if not os.listdir(image_dir):
        update.message.reply_text("I couldn't find any images in your PDF file.")
    else:
        shutil.make_archive(image_dir, "zip", image_dir)

        if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
            update.message.reply_text("The images in your PDF file are too large for me to send to you. Sorry.")
        else:
            update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
            update.message.reply_document(document=open(out_filename, "rb"),
                                          caption="Here are all the images in your PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    temp_dir.cleanup()
    tf.close()
    os.remove(out_filename)

    return ConversationHandler.END


# Gets the PDF cover in jpg format
@run_async
def pdf_to_img(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    update.message.reply_text("Converting your PDF file into images.", reply_markup=ReplyKeyboardRemove())

    temp_dir = tempfile.TemporaryDirectory(prefix="PDF_Image_")
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    filename = tf.name
    image_filename = tempfile.NamedTemporaryFile(dir=image_dir, prefix="PDF_Image_", suffix=".jpg").name
    out_filename = image_dir + ".zip"

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    with wand.image.Image(filename=filename, resolution=300) as img:
        with img.convert("jpg") as converted:
            converted.save(filename=image_filename)

    shutil.make_archive(image_dir, "zip", image_dir)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The images of your PDF file are too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here are your PDF file images.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    temp_dir.cleanup()
    tf.close()
    os.remove(out_filename)

    return ConversationHandler.END


# Asks user for rotation degree
@run_async
def ask_rotate_degree(bot, update):
    keyboard = [["90"], ["180"], ["270"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("Please select the degrees that you'll like to rotate your PDF file in clockwise.",
                              reply_markup=reply_markup)

    return WAIT_ROTATE_DEGREE


# Rotates the PDF file with the given degree
@run_async
def rotate_pdf(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    rotate_degree = int(update.message.text)
    update.message.reply_text("Rotating your PDF file clockwise by %d degrees." % rotate_degree,
                              reply_markup=ReplyKeyboardRemove())

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix="Rotated_", suffix=".pdf")]
    filename = temp_files[0].name
    out_filename = temp_files[1].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        pdf_writer.addPage(page.rotateClockwise(rotate_degree))

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The rotated PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your rotated PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Asks for horizontal scaling factor or new width
@run_async
def ask_scale_x(bot, update):
    if update.message.text == "Scale By":
        update.message.reply_text("Please send me the scaling factor for the horizontal axis. For example, "
                                  "2 will double the horizontal axis and 0.5 will half the horizontal axis.",
                                  reply_markup=ReplyKeyboardRemove())

        return WAIT_SCALE_BY_X
    else:
        update.message.reply_text("Please send me the new width.", reply_markup=ReplyKeyboardRemove())

        return WAIT_SCALE_TO_X


# Checks for horizontal scaling factor and asks for vertical scaling factor
@run_async
def ask_scale_by_y(bot, update, user_data):
    scale_x = update.message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        update.message.reply_text("The scaling factor that you sent me is invalid. Please try again.")

        return WAIT_SCALE_BY_X

    user_data["scale_by_x"] = scale_x
    update.message.reply_text("Please send me the scaling factor for the vertical axis. For example, 2 will double "
                              "the vertical axis and 0.5 will half the vertical axis.")

    return WAIT_SCALE_BY_Y


# Checks for vertical scaling factor and scale PDF file
@run_async
def pdf_scale_by(bot, update, user_data):
    if "pdf_id" not in user_data or "scale_by_x" not in user_data:
        return ConversationHandler.END

    scale_y = update.message.text

    try:
        scale_y = float(scale_y)
    except ValueError:
        update.message.reply_text("The scaling factor that you sent me is invalid. Please try again.")

        return WAIT_SCALE_BY_Y

    file_id = user_data["pdf_id"]
    scale_x = user_data["scale_by_x"]
    update.message.reply_text("Scaling your PDF file, horizontally by {:g} and vertically by {:g}.".
                              format(scale_x, scale_y))

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix="Scaled_By_", suffix=".pdf")]
    filename = temp_files[0].name
    out_filename = temp_files[1].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        page.scale(scale_x, scale_y)
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The scaled PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your scaled PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    if user_data["scale_by_x"] == scale_x:
        del user_data["scale_by_x"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Checks for width and asks for height
@run_async
def ask_scale_to_y(bot, update, user_data):
    scale_x = update.message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        update.message.reply_text("The width that you sent me is invalid. Please try again.")

        return WAIT_SCALE_TO_X

    user_data["scale_to_x"] = scale_x
    update.message.reply_text("Please send me the new height.")

    return WAIT_SCALE_TO_Y


# Checks for height and scale PDF file
@run_async
def pdf_scale_to(bot, update, user_data):
    if "pdf_id" not in user_data or "scale_to_x" not in user_data:
        return ConversationHandler.END

    scale_y = update.message.text

    try:
        scale_y = float(scale_y)
    except ValueError:
        update.message.reply_text("The height that you sent me is invalid. Please try again.")

        return WAIT_SCALE_TO_Y

    file_id = user_data["pdf_id"]
    scale_x = user_data["scale_to_x"]
    update.message.reply_text("Scaling your PDF file with width of {:g} and height of {:g}.".
                              format(scale_x, scale_y))

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix="Scaled_To_", suffix=".pdf")]
    filename = temp_files[0].name
    out_filename = temp_files[1].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        page.scaleTo(scale_x, scale_y)
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The scaled PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your scaled PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    if user_data["scale_to_x"] == scale_x:
        del user_data["scale_to_x"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Asks for split page range
@run_async
def ask_split_range(bot, update):
    update.message.reply_text("Please send me the range of pages that you will like to keep. You can use ⚡ *INSTANT "
                              "VIEW* from below or refer to [here](http://telegra.ph/Telegram-PDF-Bot-07-16) for "
                              "some range examples.", parse_mode="markdown", reply_markup=ReplyKeyboardRemove())

    return WAIT_SPLIT_RANGE


# Splits the PDF file with the given page range
@run_async
def split_pdf(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    file_id = user_data["pdf_id"]
    split_range = update.message.text
    update.message.reply_text("Splitting your PDF file.")

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix="Split_", suffix=".pdf")]
    filename = temp_files[0].name
    out_filename = temp_files[1].name

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    command = "python3 pdfcat.py -o {out_filename} {in_filename} {split_range}". \
        format(out_filename=out_filename, in_filename=filename, split_range=split_range)

    process = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    process_out, process_err = process.communicate()

    if process.returncode != 0 or not os.path.exists(out_filename) or "[Errno" in process_err.decode("utf8").strip():
        update.message.reply_text("The range is invalid. Please send me the range again.")

        return WAIT_SPLIT_RANGE

    reader = PdfFileReader(out_filename)
    if reader.getNumPages() == 0:
        os.remove(filename)
        os.remove(out_filename)
        update.message.reply_text("The range is invalid. Please send me the range again.")

        return WAIT_SPLIT_RANGE

    if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The split PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your split PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Cancels feedback opteration
@run_async
def cancel(bot, update):
    update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Sends a message to a specified user
def send(bot, update, args):
    if update.message.from_user.id == DEV_TELE_ID:
        tele_id = int(args[0])
        message = " ".join(args[1:])

        try:
            bot.send_message(tele_id, message)
        except Exception as e:
            LOGGER.exception(e)
            bot.send_message(DEV_TELE_ID, "Failed to send message")


def error(bot, update, error):
    LOGGER.warning('Update "%s" caused error "%s"' % (update, error))


if __name__ == '__main__':
    main()
