import logbook
import os
import re
import shlex
import shutil
import sys
import tempfile
import wand.image

from dotenv import load_dotenv
from feedback_bot import feedback_cov_handler
from logbook import Logger, StreamHandler
from PIL import Image as PillowImage
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from PyPDF2.utils import PdfReadError
from subprocess import Popen, PIPE

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction
from telegram.constants import *
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, RegexHandler, Filters
from telegram.ext.dispatcher import run_async

from constants import *
from utils import check_pdf, open_pdf, work_on_pdf, send_result
from merge import merge_cov_handler

load_dotenv()
HOST = '.appspot.com/'
APP_URL = f'{os.environ.get("GAE_APPLICATION", "")}{HOST}'
PORT = int(os.environ.get('PORT', '8443'))
TELE_TOKEN = os.environ.get('TELE_TOKEN_BETA', os.environ.get('TELE_TOKEN'))
DEV_TELE_ID = int(os.environ.get('DEV_TELE_ID'))
DEV_EMAIL = os.environ.get('DEV_EMAIL', 'sample@email.com')

CHANNEL_NAME = 'pdf2botdev'
BOT_NAME = 'pdf2bot'
TIMEOUT = 20


def main():
    # Setup logging
    logbook.set_datetime_format('local')
    format_string = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}: {record.message}'
    StreamHandler(sys.stdout, format_string=format_string).push_application()
    log = Logger()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        TELE_TOKEN, use_context=True, request_kwargs={'connect_timeout': TIMEOUT, 'read_timeout': TIMEOUT})

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler('start', start_msg))
    dispatcher.add_handler(CommandHandler('help', help_msg))
    dispatcher.add_handler(CommandHandler('donate', donate_msg))
    # dispatcher.add_handler(compare_cov_handler())
    dispatcher.add_handler(merge_cov_handler())
    dispatcher.add_handler(photo_cov_handler())
    dispatcher.add_handler(watermark_cov_handler())
    dispatcher.add_handler(doc_cov_handler())
    dispatcher.add_handler(feedback_cov_handler())
    dispatcher.add_handler(CommandHandler('send', send, Filters.user(DEV_TELE_ID), pass_args=True))

    # log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL != HOST:
        updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice('Bot started webhook')
    else:
        updater.start_polling()
        log.notice('Bot started polling')

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


@run_async
def start_msg(update, _):
    """
    Send start message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = 'Welcome to PDF Bot!\n\n'
    text += 'I can compare, decrypt, encrypt, merge, rotate, scale, split and add watermark to a PDF file.\n\n '
    text += 'I can also extract images in a PDF file and convert a PDF file into images.\n\n'
    text += 'I can also also beautify and convert photos into PDF format.\n\n'
    text += 'Type /help to see how to use me.'

    update.message.reply_text(text)


@run_async
def help_msg(update, _):
    """
    Send help message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = 'You can perform most of the tasks simply by sending me a PDF file. You can then select a task and I ' \
           'will guide you through each of the tasks.\n\n'
    text += 'If you want to compare, merge or add watermark to PDF files, you will have to use the /compare, ' \
            '/merge or /watermark commands respectively.\n\n'
    text += 'If you want to beautify and convert photos into PDF format, simply send me a photo or ' \
            'use the /photo command to deal with multiple photos.\n\n'
    text += 'Please note that I can only download files up to 20 MB in size and upload files up to 50 MB in size. ' \
            'If the result files are too large, I will not be able to send you the file.\n\n'

    keyboard = [[InlineKeyboardButton('Join Channel', f'https://t.me/{CHANNEL_NAME}'),
                 InlineKeyboardButton('Rate me', f'https://t.me/storebot?start={BOT_NAME}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(text, reply_markup=reply_markup)


@run_async
def donate_msg(update, _):
    """
    Send donate message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = f'Want to help keep me online? Please donate to {DEV_EMAIL} through PayPal.\n\n' \
           f'Donations help me to stay on my server and keep running.'

    update.message.reply_text(text)


# Create a watermark conversation handler
def watermark_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('watermark', watermark)],
        states={
            WAIT_WATERMARK_SOURCE_FILE: [MessageHandler(Filters.document, receive_watermark_source_file,
                                                        pass_user_data=True)],
            WAIT_WATERMARK_FILE: [MessageHandler(Filters.document, receive_watermark_file, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    return conv_handler


# Start the watermark conversation
@run_async
def watermark(bot, update):
    update.message.reply_text('Please send me the PDF file that you will like to add a watermark or type /cancel to '
                              'cancel this operation.')

    return WAIT_WATERMARK_SOURCE_FILE


# Receive and check for the source PDF file
@run_async
def receive_watermark_source_file(bot, update, user_data):
    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WATERMARK_SOURCE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    user_data['watermark_file_id'] = update.message.document.file_id
    update.message.reply_text('Please send me the watermark in PDF format.')

    return WAIT_WATERMARK_FILE


# Receive and check for the watermark PDF file and watermark the PDF file
@run_async
def receive_watermark_file(bot, update, user_data):
    if 'watermark_file_id' not in user_data:
        return ConversationHandler.END

    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_WATERMARK_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    return add_pdf_watermark(bot, update, user_data, update.message.document.file_id)


# Add watermark to PDF file
def add_pdf_watermark(bot, update, user_data, watermark_file_id):
    if 'watermark_file_id' not in user_data:
        return ConversationHandler.END

    source_file_id = user_data['watermark_file_id']
    update.message.reply_text('Adding the watermark to your PDF file...')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Watermarked_', suffix='.pdf'))
    source_filename, watermark_filename, out_filename = [x.name for x in temp_files]

    # Download PDF files
    source_pdf_file = bot.get_file(source_file_id)
    source_pdf_file.download(custom_path=source_filename)
    watermark_pdf_file = bot.get_file(watermark_file_id)
    watermark_pdf_file.download(custom_path=watermark_filename)

    pdf_reader = open_pdf(source_filename, update, 'source')
    if pdf_reader:
        watermark_reader = open_pdf(watermark_filename, update, 'watermark')
        if watermark_reader:
            # Add watermark
            pdf_writer = PdfFileWriter()
            for page in pdf_reader.pages:
                page.mergePage(watermark_reader.getPage(0))
                pdf_writer.addPage(page)

            with open(out_filename, 'wb') as f:
                pdf_writer.write(f)

            send_result(update, out_filename, 'watermarked')

    # Clean up memory and files
    if user_data['watermark_file_id'] == source_file_id:
        del user_data['watermark_file_id']
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Create a PDF conversation handler
def doc_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.document, check_doc, pass_user_data=True),
                      MessageHandler(Filters.photo, check_photo, pass_user_data=True)],
        states={
            WAIT_TASK: [RegexHandler('^Cover$', get_pdf_cover_img, pass_user_data=True),
                        RegexHandler('^Decrypt$', ask_decrypt_pw),
                        RegexHandler('^Encrypt$', ask_encrypt_pw),
                        RegexHandler('^Extract Images$', get_pdf_img, pass_user_data=True),
                        RegexHandler('^To Images$', pdf_to_img, pass_user_data=True),
                        RegexHandler('^Rotate$', ask_rotate_degree),
                        RegexHandler('^Scale By$', ask_scale_x),
                        RegexHandler('^Scale To$', ask_scale_x),
                        RegexHandler('^Split$', ask_split_range),
                        RegexHandler('^(Beautify|Convert)$', receive_photo_task, pass_user_data=True),
                        RegexHandler('^Rename$', ask_pdf_new_name)],
            WAIT_DECRYPT_PW: [MessageHandler(Filters.text, decrypt_pdf, pass_user_data=True)],
            WAIT_ENCRYPT_PW: [MessageHandler(Filters.text, encrypt_pdf, pass_user_data=True)],
            WAIT_ROTATE_DEGREE: [RegexHandler('^(90|180|270)$', rotate_pdf, pass_user_data=True)],
            WAIT_SCALE_BY_X: [MessageHandler(Filters.text, ask_scale_by_y, pass_user_data=True)],
            WAIT_SCALE_BY_Y: [MessageHandler(Filters.text, pdf_scale_by, pass_user_data=True)],
            WAIT_SCALE_TO_X: [MessageHandler(Filters.text, ask_scale_to_y, pass_user_data=True)],
            WAIT_SCALE_TO_Y: [MessageHandler(Filters.text, pdf_scale_to, pass_user_data=True)],
            WAIT_SPLIT_RANGE: [MessageHandler(Filters.text, split_pdf, pass_user_data=True)],
            WAIT_FILENAME: [MessageHandler(Filters.text, rename_pdf, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel), RegexHandler('^Cancel$', cancel)],
        allow_reentry=True
    )

    return conv_handler


# Check if the document is a photo or PDF file and if it exceeds the download size limit
@run_async
def check_doc(bot, update, user_data):
    doc = update.message.document
    mime_type = doc.mime_type

    if mime_type.startswith('image'):
        return check_photo(bot, update, user_data, doc)
    if not mime_type.endswith('pdf'):
        return ConversationHandler.END
    elif doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text('The PDF file you sent is too large for me to download. '
                                  'Sorry that I can\'t perform any tasks on your PDF file.')

        return ConversationHandler.END

    user_data['pdf_id'] = doc.file_id

    keywords = sorted(['Decrypt', 'Encrypt', 'Rotate', 'Scale By', 'Scale To', 'Split', 'Cover', 'To Images',
                       'Extract Images', 'Rename'])
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append(['Cancel'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text('Please select the task that you\'ll like to perform.',
                              reply_markup=reply_markup)

    return WAIT_TASK


# Check for photo
@run_async
def check_photo(bot, update, user_data, photo_file=None):
    if photo_file is None:
        photo_file = update.message.photo[-1]

    if photo_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text('The photo you sent is too large for me to download. '
                                  'Sorry that I can\'t beautify and convert your photo.')

        return ConversationHandler.END

    user_data['photo_id'] = photo_file.file_id
    keyboard = [['Beautify', 'Convert'], ['Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text('Please select the task that you\'ll like to perform.',
                              reply_markup=reply_markup)

    return WAIT_TASK


def receive_photo_task(bot, update, user_data):
    if 'photo_id' not in user_data:
        return ConversationHandler.END

    file_id = user_data['photo_id']
    if update.message.text.lower() == 'beautify':
        convert_photo(bot, update, [file_id], is_beautify=True)
    else:
        convert_photo(bot, update, [file_id], is_beautify=False)

    if user_data['photo_id'] == file_id:
        del user_data['photo_id']

    return ConversationHandler.END


# Get the PDF cover in jpg format
@run_async
def get_pdf_cover_img(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    file_id = user_data['pdf_id']
    update.message.reply_text('Extracting a cover preview for your PDF file...', reply_markup=ReplyKeyboardRemove())

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Cover_', suffix='.jpg'))
    filename, tmp_filename, out_filename = [x.name for x in temp_files]

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_reader = open_pdf(filename, update)
    if pdf_reader:
        pdf_writer = PdfFileWriter()
        pdf_writer.addPage(pdf_reader.getPage(0))

        with open(tmp_filename, 'wb') as f:
            pdf_writer.write(f)

        with wand.image.Image(filename=tmp_filename, resolution=300) as img:
            with img.convert('jpg') as converted:
                converted.save(filename=out_filename)

        send_result(update, out_filename, 'cover preview')

    # Clean up memory and files
    if user_data['pdf_id'] == file_id:
        del user_data['pdf_id']
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Ask user for decryption password
@run_async
def ask_decrypt_pw(bot, update):
    update.message.reply_text('Please send me the password to decrypt your PDF file.',
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_DECRYPT_PW


# Decrypt the PDF file with the given password
@run_async
def decrypt_pdf(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    file_id = user_data['pdf_id']
    pw = update.message.text
    update.message.reply_text('Decrypting your PDF file...')

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix='Decrypted_', suffix='.pdf')]
    filename, out_filename = [x.name for x in temp_files]

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    pdf_reader = None

    try:
        pdf_reader = PdfFileReader(open(filename, 'rb'))
    except PdfReadError:
        text = 'Your PDF file seems to be invalid and I couldn\'t open and read it. Operation cancelled.'
        update.message.reply_text(text)

    if pdf_reader and not pdf_reader.isEncrypted:
        update.message.reply_text('Your PDF file is not encrypted. Operation cancelled.')
    elif pdf_reader:
        try:
            if pdf_reader.decrypt(pw) == 0:
                update.message.reply_text('The decryption password is incorrect. Please send it again.')

                return WAIT_DECRYPT_PW
        except NotImplementedError:
            update.message.reply_text('The PDF file is encrypted with a method that I cannot decrypt. Sorry.')

            return ConversationHandler.END

        pdf_writer = PdfFileWriter()
        for page in pdf_reader.pages:
            pdf_writer.addPage(page)

        with open(out_filename, 'wb') as f:
            pdf_writer.write(f)

        send_result(update, out_filename, 'decrypted')

    # Clean up memory and files
    if user_data['pdf_id'] == file_id:
        del user_data['pdf_id']
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Ask user for encryption password
@run_async
def ask_encrypt_pw(bot, update):
    update.message.reply_text('Please send me the password to encrypt your PDF file.',
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_ENCRYPT_PW


# Encrypt the PDF file with the given password
@run_async
def encrypt_pdf(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Encrypting your PDF file...')
    work_on_pdf(bot, update, user_data, 'encrypted', encrypt_pw=update.message.text)

    return ConversationHandler.END


# Get the images in the PDF file
@run_async
def get_pdf_img(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    file_id = user_data['pdf_id']
    update.message.reply_text('Extracting all the images in your PDF file...', reply_markup=ReplyKeyboardRemove())

    temp_dir = tempfile.TemporaryDirectory(prefix='Images_')
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    filename = tf.name
    out_filename = image_dir + '.zip'

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    pdf_reader = open_pdf(filename, update)

    if pdf_reader:
        # Find and write all images
        for page in pdf_reader.pages:
            if '/Resources' in page and '/XObject' in page['/Resources']:
                x_object = page['/Resources']['/XObject'].getObject()

                for obj in x_object:
                    if x_object[obj]['/Subtype'] == '/Image':
                        size = (x_object[obj]['/Width'], x_object[obj]['/Height'])

                        try:
                            data = x_object[obj].getData()
                        except:
                            continue

                        if x_object[obj]['/ColorSpace'] == '/DeviceRGB':
                            mode = 'RGB'
                        else:
                            mode = 'P'

                        if x_object[obj]['/Filter'] == '/FlateDecode':
                            try:
                                img = PillowImage.frombytes(mode, size, data)
                                img.save(tempfile.NamedTemporaryFile(dir=image_dir, suffix='.png').name)
                            except TypeError:
                                pass
                        elif x_object[obj]['/Filter'] == '/DCTDecode':
                            with open(tempfile.NamedTemporaryFile(dir=image_dir, suffix='.jpg').name, 'wb') as img:
                                img.write(data)
                        elif x_object[obj]['/Filter'] == '/JPXDecode':
                            with open(tempfile.NamedTemporaryFile(dir=image_dir, suffix='.jp2').name, 'wb') as img:
                                img.write(data)

        if not os.listdir(image_dir):
            update.message.reply_text('I couldn\'t find any images in your PDF file.')
        else:
            shutil.make_archive(image_dir, 'zip', image_dir)
            send_result(update, out_filename, 'images in your', 'Here are all the images in your PDF file.')
            os.remove(out_filename)

    # Clean up memory and files
    if user_data['pdf_id'] == file_id:
        del user_data['pdf_id']
    temp_dir.cleanup()
    tf.close()

    return ConversationHandler.END


# Get the PDF file in jpg format
@run_async
def pdf_to_img(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    file_id = user_data['pdf_id']
    update.message.reply_text('Converting your PDF file into images...', reply_markup=ReplyKeyboardRemove())

    # Setup temporary files
    temp_dir = tempfile.TemporaryDirectory(prefix='PDF_Image_')
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    filename = tf.name
    image_filename = tempfile.NamedTemporaryFile(dir=image_dir, prefix='PDF_Image_', suffix='.jpg').name
    out_filename = image_dir + '.zip'

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    with wand.image.Image(filename=filename, resolution=300) as img:
        with img.convert('jpg') as converted:
            converted.save(filename=image_filename)

    shutil.make_archive(image_dir, 'zip', image_dir)
    send_result(update, out_filename, 'images of your', 'Here are the images of your PDF file.')

    # Clean up memory and files
    if user_data['pdf_id'] == file_id:
        del user_data['pdf_id']
    temp_dir.cleanup()
    tf.close()
    os.remove(out_filename)

    return ConversationHandler.END


# Ask user for new filename
@run_async
def ask_pdf_new_name(bot, update):
    update.message.reply_text('Please send me the filename that you\'ll like to rename your PDF file into.',
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_FILENAME


# Rename the PDF file with the new filename
@run_async
def rename_pdf(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    text = re.sub('\.pdf$', '', update.message.text)
    invalid_chars = '\/*?:\'<>|'
    if set(text) & set(invalid_chars):
        update.message.reply_text('Filenames can\'t contain any of the following characters:\n{}\n'
                                  'Please try again.'.format(invalid_chars))

        return WAIT_FILENAME

    file_id = user_data['pdf_id']
    new_name = '{}.pdf'.format(text)
    update.message.reply_text('Renaming your PDF file into *{}*...'.format(new_name), parse_mode='Markdown')

    # Setup temp files
    temp_file = tempfile.NamedTemporaryFile()
    temp_dir = tempfile.TemporaryDirectory()
    filename = temp_file.name

    # Download PDF file
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    new_filename = '{}/{}'.format(temp_dir.name, new_name)
    shutil.move(filename, new_filename)
    send_result(update, new_filename, 'renamed')

    # Clean up memory and files
    if user_data['pdf_id'] == file_id:
        del user_data['pdf_id']
    temp_dir.cleanup()
    try:
        temp_file.close()
    except FileNotFoundError:
        pass

    return ConversationHandler.END


# Ask user for rotation degree
@run_async
def ask_rotate_degree(bot, update):
    keyboard = [['90'], ['180'], ['270']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text('Please select the degrees that you\'ll like to rotate your PDF file in clockwise.',
                              reply_markup=reply_markup)

    return WAIT_ROTATE_DEGREE


# Rotate the PDF file with the given degree
@run_async
def rotate_pdf(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    degree = int(update.message.text)
    update.message.reply_text(f'Rotating your PDF file clockwise by {degree} degrees...',
                              reply_markup=ReplyKeyboardRemove())
    work_on_pdf(bot, update, user_data, 'rotated', rotate_degree=degree)

    return ConversationHandler.END


# Ask for horizontal scaling factor or new width
@run_async
def ask_scale_x(bot, update):
    if update.message.text == 'Scale By':
        update.message.reply_text('Please send me the scaling factor for the horizontal axis. For example, '
                                  '2 will double the horizontal axis and 0.5 will half the horizontal axis.',
                                  reply_markup=ReplyKeyboardRemove())

        return WAIT_SCALE_BY_X
    else:
        update.message.reply_text('Please send me the new width.', reply_markup=ReplyKeyboardRemove())

        return WAIT_SCALE_TO_X


# Check for horizontal scaling factor and ask for vertical scaling factor
@run_async
def ask_scale_by_y(bot, update, user_data):
    scale_x = update.message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        update.message.reply_text('The scaling factor that you sent me is invalid. Please try again.')

        return WAIT_SCALE_BY_X

    user_data['scale_by_x'] = scale_x
    update.message.reply_text('Please send me the scaling factor for the vertical axis. For example, 2 will double '
                              'the vertical axis and 0.5 will half the vertical axis.')

    return WAIT_SCALE_BY_Y


# Check for vertical scaling factor and scale PDF file
@run_async
def pdf_scale_by(bot, update, user_data):
    if 'pdf_id' not in user_data or 'scale_by_x' not in user_data:
        return ConversationHandler.END

    scale_y = update.message.text
    try:
        scale_y = float(scale_y)
    except ValueError:
        update.message.reply_text('The scaling factor that you sent me is invalid. Please try again.')

        return WAIT_SCALE_BY_Y

    scale_x = user_data['scale_by_x']
    update.message.reply_text(f'Scaling your PDF file, horizontally by {scale_x} and vertically by {scale_y}...')
    work_on_pdf(bot, update, user_data, 'scaled', scale_by=(scale_x, scale_y))

    if user_data['scale_by_x'] == scale_x:
        del user_data['scale_by_x']

    return ConversationHandler.END


# Checks for width and asks for height
@run_async
def ask_scale_to_y(bot, update, user_data):
    scale_x = update.message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        update.message.reply_text('The width that you sent me is invalid. Please try again.')

        return WAIT_SCALE_TO_X

    user_data['scale_to_x'] = scale_x
    update.message.reply_text('Please send me the new height.')

    return WAIT_SCALE_TO_Y


# Checks for height and scale PDF file
@run_async
def pdf_scale_to(bot, update, user_data):
    if 'pdf_id' not in user_data or 'scale_to_x' not in user_data:
        return ConversationHandler.END

    scale_y = update.message.text

    try:
        scale_y = float(scale_y)
    except ValueError:
        update.message.reply_text('The height that you sent me is invalid. Please try again.')

        return WAIT_SCALE_TO_Y

    scale_x = user_data['scale_to_x']
    update.message.reply_text(f'Scaling your PDF file with width of {scale_x} and height of {scale_y}...')
    work_on_pdf(bot, update, user_data, 'scaled', scale_to=(scale_x, scale_y))

    if user_data['scale_to_x'] == scale_x:
        del user_data['scale_to_x']

    return ConversationHandler.END


# Asks for split page range
@run_async
def ask_split_range(bot, update):
    update.message.reply_text('Please send me the range of pages that you will like to keep. You can use ⚡ *INSTANT '
                              'VIEW* from below or refer to [here](http://telegra.ph/Telegram-PDF-Bot-07-16) for '
                              'some range examples.', parse_mode='markdown', reply_markup=ReplyKeyboardRemove())

    return WAIT_SPLIT_RANGE


# Splits the PDF file with the given page range
@run_async
def split_pdf(bot, update, user_data):
    if 'pdf_id' not in user_data:
        return ConversationHandler.END

    file_id = user_data['pdf_id']
    split_range = update.message.text
    update.message.reply_text('Splitting your PDF file...')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix='Split_', suffix='.pdf')]
    filename, out_filename = [x.name for x in temp_files]

    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    pdf_reader = open_pdf(filename, update)

    if pdf_reader:
        command = 'python3 pdfcat.py -o {out_filename} {in_filename} {split_range}'. \
            format(out_filename=out_filename, in_filename=filename, split_range=split_range)

        proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
        proc_out, proc_err = proc.communicate()

        if proc.returncode != 0 or not os.path.exists(out_filename):
            LOGGER.error(proc_err.decode('utf8'))
            update.message.reply_text('Something went wrong, please try again.')

            return ConversationHandler.END

        reader = PdfFileReader(out_filename)
        if reader.getNumPages() == 0:
            for tf in temp_files:
                tf.close()
            update.message.reply_text('The range is invalid. Please send me the range again.')

            return WAIT_SPLIT_RANGE

        send_result(update, out_filename, 'split')

    # Clean up memory and files
    if user_data['pdf_id'] == file_id:
        del user_data['pdf_id']
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


# Sends a message to a specified user
def send(bot, update, args):
    tele_id = int(args[0])
    message = ' '.join(args[1:])

    try:
        bot.send_message(tele_id, message)
    except Exception as e:
        LOGGER.exception(e)
        bot.send_message(DEV_TELE_ID, 'Failed to send message')


def error_callback(update, context):
    log = Logger()
    log.warn(f'Update "{update}" caused error "{context.error}"')


if __name__ == '__main__':
    main()
