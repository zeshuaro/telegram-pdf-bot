import os
import pdf2image
import shutil
import tempfile

from logbook import Logger
from PIL import Image
from PyPDF2 import PdfFileWriter
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import ConversationHandler
from telegram.ext import run_async
from telegram.parsemode import ParseMode

from pdf_bot.constants import *
from pdf_bot.utils import open_pdf, send_result_file, check_user_data, get_support_markup
from pdf_bot.stats import update_stats


@run_async
def get_pdf_preview(update, context):
    """
    Get the PDF preview in JPEG format
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if not check_user_data(update, PDF_INFO, user_data):
        return ConversationHandler.END

    update.effective_message.reply_text('Extracting a preview for your PDF file', reply_markup=ReplyKeyboardRemove())

    with tempfile.NamedTemporaryFile() as tf1:
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf1.name)

        pdf_reader = open_pdf(tf1.name, update)
        if pdf_reader:
            # Get first page of PDF file
            pdf_writer = PdfFileWriter()
            pdf_writer.addPage(pdf_reader.getPage(0))

            with tempfile.NamedTemporaryFile() as tf2:
                # Write cover preview PDF file
                with open(tf2.name, 'wb') as f:
                    pdf_writer.write(f)

                with tempfile.TemporaryDirectory() as dir_name:
                    # Convert cover preview to JPEG
                    out_fn = os.path.join(dir_name, f'Preview_{os.path.splitext(file_name)[0]}.png')
                    imgs = pdf2image.convert_from_path(tf2.name, fmt='png')
                    imgs[0].save(out_fn)

                    # Send result file
                    send_result_file(update, out_fn)

    # Clean up memory and files
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


@run_async
def ask_photo_results_type(update, context):
    """
    Ask for the photo results file type
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the file type
    """
    if update.effective_message.text == EXTRACT_IMG:
        return_type = WAIT_EXTRACT_PHOTO_TYPE
    else:
        return_type = WAIT_TO_PHOTO_TYPE

    keyboard = [[PHOTOS, ZIPPED], [BACK]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text('Select the result file format to be sent back to you.',
                                        reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    return return_type


@run_async
def pdf_to_photos(update, context):
    """
    Convert the PDF file into JPEG photos
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if not check_user_data(update, PDF_INFO, user_data):
        return ConversationHandler.END

    update.effective_message.reply_text('Converting your PDF file into photos', reply_markup=ReplyKeyboardRemove())
    with tempfile.NamedTemporaryFile() as tf:
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            # Setup the directory for the photos
            dir_name = os.path.join(tmp_dir_name, 'PDF_Photos')
            os.mkdir(dir_name)

            # Convert the PDF file into photos
            pdf2image.convert_from_path(tf.name, output_folder=dir_name, output_file=os.path.splitext(file_name)[0],
                                        fmt='png')

            # Handle the result photos
            handle_result_photos(update, dir_name)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


@run_async
def get_pdf_photos(update, context):
    """
    Get all the photos in the PDF file
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if not check_user_data(update, PDF_INFO, user_data):
        return ConversationHandler.END

    update.effective_message.reply_text('Extracting all the photos in your PDF file',
                                        reply_markup=ReplyKeyboardRemove())
    with tempfile.NamedTemporaryFile() as tf:
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)
        pdf_reader = open_pdf(tf.name, update)

        if pdf_reader is not None:
            with tempfile.TemporaryDirectory() as tmp_dir_name:
                # Setup the directory for the photos
                dir_name = os.path.join(tmp_dir_name, 'Photos_In_PDF')
                os.mkdir(dir_name)
                root_file_name = os.path.splitext(file_name)[0]
                i = 0
                log = Logger()

                # Find and store all photos
                for page in pdf_reader.pages:
                    if '/Resources' in page and '/XObject' in page['/Resources']:
                        x_object = page['/Resources']['/XObject'].getObject()

                        for obj in x_object:
                            if x_object[obj]['/Subtype'] == '/Image':
                                size = (x_object[obj]['/Width'], x_object[obj]['/Height'])
                                try:
                                    data = x_object[obj].getData()
                                except Exception as e:
                                    log.error(e)

                                    continue

                                if x_object[obj]['/Filter'] == '/FlateDecode':
                                    if x_object[obj]['/ColorSpace'] == '/DeviceRGB':
                                        mode = 'RGB'
                                    else:
                                        mode = 'P'

                                    try:
                                        img = Image.frombytes(mode, size, data)
                                        img.save(os.path.join(dir_name, f'{root_file_name}-{i}.png'))
                                        i += 1
                                    except TypeError:
                                        pass
                                elif x_object[obj]['/Filter'] == '/DCTDecode':
                                    with open(os.path.join(dir_name, f'{root_file_name}-{i}.jpg'), 'wb') as img:
                                        img.write(data)
                                        i += 1
                                elif x_object[obj]['/Filter'] == '/JPXDecode':
                                    with open(os.path.join(dir_name, f'{root_file_name}-{i}.jp2'), 'wb') as img:
                                        img.write(data)
                                        i += 1

                if not os.listdir(dir_name):
                    update.effective_message.reply_text('I couldn\'t find any photos in your PDF file.')
                else:
                    handle_result_photos(update, dir_name)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def handle_result_photos(update, dir_name):
    """
    Handle the result photos
    Args:
        update: the update object
        dir_name: the string of directory name containing the photos

    Returns:
        None
    """
    message = update.effective_message
    if message.text == PHOTOS:
        photos = []
        for photo_name in sorted(os.listdir(dir_name)):
            if len(photos) != 0 and len(photos) % MAX_MEDIA_GROUP == 0:
                message.reply_media_group(photos)
                del photos[:]

            photos.append(InputMediaPhoto(open(os.path.join(dir_name, photo_name), 'rb')))

        if photos:
            message.reply_media_group(photos)

        message.reply_text('See above for all your photos', reply_markup=get_support_markup())
        update_stats(update)
    else:
        # Compress the directory of photos
        shutil.make_archive(dir_name, 'zip', dir_name)

        # Send result file
        send_result_file(update, f'{dir_name}.zip')
