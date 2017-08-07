#!/usr/bin/env python3
# coding: utf-8

import dotenv
import langdetect
import logging
import os
import shlex
import smtplib
import string
import random
import requests

from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from subprocess import Popen, PIPE
from wand.image import Image

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import *
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, RegexHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_cov_states import *

# Enable logging
logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %I:%M:%S %p',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
dotenv.load(dotenv_path)
app_url = os.environ.get("APP_URL")
port = int(os.environ.get('PORT', '5000'))

telegram_token = os.environ.get("TELEGRAM_TOKEN_BETA") if os.environ.get("TELEGRAM_TOKEN_BETA") \
    else os.environ.get("TELEGRAM_TOKEN")
dev_tele_id = int(os.environ.get("DEV_TELE_ID"))
dev_email = os.environ.get("DEV_EMAIL") if os.environ.get("DEV_EMAIL") else "sample@email.com"
dev_email_pw = os.environ.get("DEV_EMAIL_PW")
is_email_feedback = os.environ.get("IS_EMAIL_FEEDBACK")
smtp_host = os.environ.get("SMTP_HOST")
converter_url = os.environ.get("CONVERTER_URL", ) if os.environ.get("CONVERTER_URL") else \
    "https://github.com/yeokm1/docs-to-pdf-converter/releases/download/v1.8/docs-to-pdf-converter-1.8.jar"


def main():
    download_converter()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(telegram_token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("donate", donate))
    dp.add_handler(compare_cov_handler())
    dp.add_handler(merge_cov_handler())
    dp.add_handler(watermark_cov_handler())
    dp.add_handler(pdf_cov_handler())
    dp.add_handler(feedback_cov_handler())
    dp.add_handler(CommandHandler("send", send, pass_args=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if app_url:
        updater.start_webhook(listen="0.0.0.0",
                              port=port,
                              url_path=telegram_token)
        updater.bot.set_webhook(app_url + telegram_token)
    else:
        updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def download_converter():
    if not os.path.exists("docs-to-pdf-converter-1.8.jar"):
        r = requests.get(converter_url)

        with open("docs-to-pdf-converter-1.8.jar", "wb") as f:
            f.write(r.content)


# Sends start message
@run_async
def start(bot, update):
    text = "Welcome to PDF Bot!\n\n"
    text += "I can compare, decrypt, encrypt, merge, rotate, scale, split and add watermark to a PDF file.\n\n"
    text += "Type /help to see how to use me."

    try:
        bot.sendMessage(update.message.from_user.id, text)
    except:
        return


# Sends help message
@run_async
def help(bot, update):
    text = "You can perform most of the tasks simply by sending me a PDF file. You can then select a task and I " \
           "will guide you through each of the tasks.\n\n"
    text += "If you want to compare, merge or add watermark to PDF files, you will have to use the /command, " \
            "/merge or /watermark commands respectively.\n\n"
    text += "Please note that I can only download files up to 20 MB in size and upload files up to 50 MB in size. " \
            "If the result files are too large, I will not be able to send you the file.\n\n"

    keyboard = [[InlineKeyboardButton("Join Channel", "https://t.me/pdf2botdev"),
                 InlineKeyboardButton("Rate me", "https://t.me/storebot?start=pdf2bot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        bot.sendMessage(update.message.from_user.id, text, reply_markup=reply_markup)
    except:
        return


# Sends donate message
@run_async
def donate(bot, update):
    text = "Want to help keep me online? Please donate to %s through PayPal.\n\nDonations help me to stay on my " \
           "server and keep running." % dev_email

    try:
        bot.send_message(update.message.from_user.id, text)
    except:
        return


# Creates a compare conversation handler
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


# Starts the compare conversation
@run_async
def compare(bot, update):
    update.message.reply_text("Please send me one of the PDF files that you will like to compare or type /cancel to "
                              "cancel this operation.\n\nPlease note that I can only look for text differences.")

    return WAIT_FIRST_COMPARE_FILE


# Receives and checks for the source PDF file
@run_async
def check_first_compare_file(bot, update, user_data):
    result = check_pdf(bot, update)

    if result == 1:
        return WAIT_FIRST_COMPARE_FILE
    elif result != 0:
        return ConversationHandler.END

    user_data["compare_file_id"] = update.message.document.file_id
    update.message.reply_text("Please send me the other PDF file that you will like to compare.")

    return WAIT_SECOND_COMPARE_FILE


# Receives and checks for the watermark PDF file and watermark the PDF file
@run_async
def check_second_compare_file(bot, update, user_data):
    if "compare_file_id" not in user_data:
        return ConversationHandler.END

    result = check_pdf(bot, update)

    if result == 1:
        return WAIT_SECOND_COMPARE_FILE
    elif result != 0:
        return ConversationHandler.END

    return compare_pdf(bot, update, user_data, update.message.document.file_id)


# Compares two PDF files
def compare_pdf(bot, update, user_data, second_file_id):
    if "compare_file_id" not in user_data:
        return ConversationHandler.END

    update.message.reply_text("Comparing your PDF files.")
    tele_id = update.message.from_user.id

    first_file_id = user_data["compare_file_id"]
    first_filename = "%d_compare_first.pdf" % tele_id
    out_filename = "%d_compared.png" % tele_id
    second_filename = "%d_compare_second.pdf" % tele_id

    source_pdf_file = bot.get_file(first_file_id)
    source_pdf_file.download(custom_path=first_filename)

    second_pdf_file = bot.get_file(second_file_id)
    second_pdf_file.download(custom_path=second_filename)

    command = "pdf-diff {first_pdf} {second_pdf}".format(first_pdf=first_filename, second_pdf=second_filename)

    process = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    process_out, process_err = process.communicate()

    if process.returncode != 0 or "[Errno" in process_err.decode("utf8").strip():
        update.message.reply_text("There are no differences between the two PDF files you sent me.")

        return ConversationHandler.END

    with open(out_filename, "wb") as f:
        f.write(process_out)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The difference result file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here are the differences between your PDF files.")

    if user_data["compare_file_id"] == first_file_id:
        del user_data["compare_file_id"]
    os.remove(first_filename)
    os.remove(second_filename)
    os.remove(out_filename)

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
    elif file_size > MAX_FILESIZE_DOWNLOAD:
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
    elif is_pdf_encrypted(bot, file_id):
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
    tele_id = update.message.from_user.id
    update.message.reply_text("Merging your files.", reply_markup=ReplyKeyboardRemove())

    merger = PdfFileMerger()
    out_filename = "%d_merged.pdf" % tele_id

    for file_id in user_data["merge_file_ids"]:
        filename = "%d_merge_source.pdf" % tele_id
        pdf_file = bot.get_file(file_id)
        pdf_file.download(custom_path=filename)
        merger.append(open(filename, "rb"))
        os.remove(filename)

    with open(out_filename, "wb") as f:
        merger.write(f)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The merged PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your merged PDF file.")

    if user_data["merge_file_ids"] == file_ids:
        del user_data["merge_file_ids"]
    if user_data["merge_filenames"] == filenames:
        del user_data["merge_filenames"]
    os.remove(out_filename)

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

    update.message.reply_text("Adding the watermark to your PDF file.")
    tele_id = update.message.from_user.id

    source_file_id = user_data["watermark_file_id"]
    source_filename = "%d_watermark_source.pdf" % tele_id
    out_filename = "%d_watermarked.pdf" % tele_id
    watermark_filename = "%d_watermark.pdf" % tele_id

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

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The watermarked PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your watermarked PDF file.")

    if user_data["watermark_file_id"] == source_file_id:
        del user_data["watermark_file_id"]
    os.remove(source_filename)
    os.remove(watermark_filename)
    os.remove(out_filename)

    return ConversationHandler.END


# Checks PDF files
def check_pdf(bot, update):
    return_type = 0
    pdf_file = update.message.document
    mime_type = pdf_file.mime_type
    file_id = pdf_file.file_id
    file_size = pdf_file.file_size

    if not mime_type.endswith("pdf"):
        return_type = 1
        update.message.reply_text("The file you sent is not a PDF file. Please try again and send me a PDF file or "
                                  "type /cancel to cancel the operation.")
    elif file_size > MAX_FILESIZE_DOWNLOAD:
        return_type = 2
        update.message.reply_text("The PDF file you sent is too large for me to download. "
                                  "Sorry that I can't process your PDF file. Operation cancelled.")
    elif is_pdf_encrypted(bot, file_id):
        return_type = 3
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or decrypt it with "
                                  "me first. Operation cancelled.")

    return return_type


# Creates a PDF conversation handler
def pdf_cov_handler():
    merged_filter = Filters.document & (Filters.forwarded | ~Filters.forwarded)

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(merged_filter, check_doc, pass_user_data=True)],

        states={
            WAIT_TASK: [RegexHandler("^Cover$", get_pdf_cover_img, pass_user_data=True),
                        RegexHandler("^Decrypt$", ask_decrypt_pw),
                        RegexHandler("^Encrypt$", ask_encrypt_pw),
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
    pdf_file = update.message.document
    mime_type = pdf_file.mime_type
    file_id = pdf_file.file_id
    file_size = pdf_file.file_size

    if not mime_type.endswith("pdf"):
        return ConversationHandler.END
    elif mime_type.endswith("pdf") and file_size > MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text("The PDF file you sent is too large for me to download. "
                                  "Sorry that I can't perform any tasks on your PDF file.")

        return ConversationHandler.END

    if is_pdf_encrypted(bot, file_id):
        keywords = ["Decrypt"]
    else:
        keywords = sorted(["Encrypt", "Rotate", "Scale By", "Scale To", "Split", "Cover"])

    user_data["pdf_id"] = file_id
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append(["Cancel"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Please select the task that you'll like to perform.",
                              reply_markup=reply_markup)

    return WAIT_TASK


# Checks if PDF file is encrypted
def is_pdf_encrypted(bot, file_id):
    filename = random_string(20)
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_reader = PdfFileReader(open(filename, "rb"))
    encrypted = pdf_reader.isEncrypted

    os.remove(filename)

    return encrypted


# Gets the PDF cover in jpg format
def get_pdf_cover_img(bot, update, user_data):
    if "pdf_id" not in user_data:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    update.message.reply_text("Extracting a cover preview for your PDF file.",
                              reply_markup=ReplyKeyboardRemove())

    file_id = user_data["pdf_id"]
    filename = "%d_cover_source.pdf" % tele_id
    tmp_filename = "%d_cover_tmp.pdf" % tele_id
    out_filename = "%d_cover.jpg" % tele_id

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_reader = PdfFileReader(open(filename, "rb"))
    pdf_writer = PdfFileWriter()
    pdf_writer.addPage(pdf_reader.getPage(0))

    with open(tmp_filename, "wb") as f:
        pdf_writer.write(f)

    with Image(filename=tmp_filename, resolution=300) as img:
        with img.convert("jpg") as converted:
            converted.save(filename=out_filename)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The cover preview is too large for me to send to you. Sorry.")
    else:
        update.message.reply_photo(photo=open(out_filename, "rb"),
                                   caption="Here is the cover preview of your PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    os.remove(filename)
    os.remove(tmp_filename)
    os.remove(out_filename)

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

    tele_id = update.message.from_user.id
    pw = update.message.text
    update.message.reply_text("Decrypting your PDF file.")

    file_id = user_data["pdf_id"]
    filename = "%d_decrypt_source.pdf" % tele_id
    out_filename = "%d_decrypted.pdf" % tele_id

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

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The decrypted PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your decrypted PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    os.remove(filename)
    os.remove(out_filename)

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

    tele_id = update.message.from_user.id
    pw = update.message.text
    update.message.reply_text("Encrypting your PDF file.")

    file_id = user_data["pdf_id"]
    filename = "%d_encrypt_source.pdf" % tele_id
    out_filename = "%d_encrypted.pdf" % tele_id

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        pdf_writer.addPage(page)

    pdf_writer.encrypt(pw)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The encrypted PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your encrypted PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    os.remove(filename)
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

    tele_id = update.message.from_user.id
    rotate_degree = int(update.message.text)
    update.message.reply_text("Rotating your PDF file clockwise by %d degrees." % rotate_degree,
                              reply_markup=ReplyKeyboardRemove())

    file_id = user_data["pdf_id"]
    filename = "%d_rotate_source.pdf" % tele_id
    out_filename = "%d_rotated.pdf" % tele_id

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        pdf_writer.addPage(page.rotateClockwise(rotate_degree))

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The rotated PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your rotated PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    os.remove(filename)
    os.remove(out_filename)

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

    scale_x = user_data["scale_by_x"]
    tele_id = update.message.from_user.id
    update.message.reply_text("Scaling your PDF file, horizontally by {:g} and vertically by {:g}.".
                              format(scale_x, scale_y))

    file_id = user_data["pdf_id"]
    filename = "%d_scale_by_source.pdf" % tele_id
    out_filename = "%d_scaled_by.pdf" % tele_id

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        page.scale(scale_x, scale_y)
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The scaled PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your scaled PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    if user_data["scale_by_x"] == scale_x:
        del user_data["scale_by_x"]
    os.remove(filename)
    os.remove(out_filename)

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

    scale_x = user_data["scale_to_x"]
    tele_id = update.message.from_user.id
    update.message.reply_text("Scaling your PDF file with width of {:g} and height of {:g}.".
                              format(scale_x, scale_y))

    file_id = user_data["pdf_id"]
    filename = "%d_scale_to_source.pdf" % tele_id
    out_filename = "%d_scaled_to.pdf" % tele_id

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        page.scaleTo(scale_x, scale_y)
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The scaled PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your scaled PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    if user_data["scale_to_x"] == scale_x:
        del user_data["scale_to_x"]
    os.remove(filename)
    os.remove(out_filename)

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

    tele_id = update.message.from_user.id
    split_range = update.message.text
    update.message.reply_text("Splitting your PDF file.")

    file_id = user_data["pdf_id"]
    filename = "%d_split_source.pdf" % tele_id
    out_filename = "%d_split.pdf" % tele_id

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

    if os.path.getsize(out_filename) > MAX_FILESIZE_UPLOAD:
        update.message.reply_text("The split PDF file is too large for me to send to you. Sorry.")
    else:
        update.message.reply_document(document=open(out_filename, "rb"),
                                      caption="Here is your split PDF file.")

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    os.remove(filename)
    os.remove(out_filename)

    return ConversationHandler.END


# Returns random string
def random_string(length):
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],

        states={
            0: [MessageHandler(Filters.text, receive_feedback)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Sends a feedback message
@run_async
def feedback(bot, update):
    update.message.reply_text("Please send me your feedback or type /cancel to cancel this operation. My developer "
                              "can understand English and Chinese.")

    return 0


# Saves a feedback
@run_async
def receive_feedback(bot, update):
    feedback_msg = update.message.text
    valid_lang = False
    langdetect.DetectorFactory.seed = 0
    langs = langdetect.detect_langs(feedback_msg)

    for lang in langs:
        if lang.lang in ("en", "zh-tw", "zh-cn"):
            valid_lang = True
            break

    if not valid_lang:
        update.message.reply_text("The feedback you sent is not in English or Chinese. Please try again.")
        return 0

    update.message.reply_text("Thank you for your feedback, I will let my developer know.")

    if is_email_feedback:
        server = smtplib.SMTP(smtp_host)
        server.ehlo()
        server.starttls()
        server.login(dev_email, dev_email_pw)

        text = "Feedback received from %d\n\n%s" % (update.message.from_user.id, update.message.text)
        message = "Subject: %s\n\n%s" % ("Telegram PDF Bot Feedback", text)
        server.sendmail(dev_email, dev_email, message)
    else:
        logger.info("Feedback received from %d: %s" % (update.message.from_user.id, update.message.text))

    return ConversationHandler.END


# Cancels feedback opteration
@run_async
def cancel(bot, update):
    update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Sends a message to a specified user
def send(bot, update, args):
    if update.message.from_user.id == dev_tele_id:
        tele_id = int(args[0])
        message = " ".join(args[1:])

        try:
            bot.send_message(tele_id, message)
        except Exception as e:
            logger.exception(e)
            bot.send_message(dev_tele_id, "Failed to send message")


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


if __name__ == '__main__':
    main()
