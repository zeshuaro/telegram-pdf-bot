import os
import pdf2image
import shutil
import tempfile

from logbook import Logger
from PIL import Image
from PyPDF2 import PdfFileWriter
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext import run_async

from pdf_bot.constants import PDF_INFO
from pdf_bot.utils import open_pdf, send_result_file


@run_async
def get_pdf_cover(update, context):
    """
    Get the PDF cover page in JPEG format
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if PDF_INFO not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Extracting a cover preview for your PDF file', reply_markup=ReplyKeyboardRemove())

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
                    out_fn = os.path.join(dir_name, f'Cover_{os.path.splitext(file_name)[0]}.png')
                    imgs = pdf2image.convert_from_path(tf2.name, fmt='png')
                    imgs[0].save(out_fn)

                    # Send result file
                    send_result_file(update, out_fn)

    # Clean up memory and files
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


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
    if PDF_INFO not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Converting your PDF file into photos', reply_markup=ReplyKeyboardRemove())
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

            # Compress the directory of photos
            shutil.make_archive(dir_name, 'zip', dir_name)

            # Send result file
            send_result_file(update, f'{dir_name}.zip')

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
    if PDF_INFO not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Extracting all the photos in your PDF file', reply_markup=ReplyKeyboardRemove())
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
                    update.message.reply_text('I couldn\'t find any photos in your PDF file.')
                else:
                    shutil.make_archive(dir_name, 'zip', dir_name)
                    send_result_file(update, f'{dir_name}.zip')

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
