import ghostscript
import locale
import os
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

            with tempfile.NamedTemporaryFile() as tf2, open(tf2.name, 'wb') as f, \
                    tempfile.TemporaryDirectory() as dir_name:
                # Write cover preview PDF file
                pdf_writer.write(f)

                # Convert cover preview to JPEG
                out_fn = os.path.join(dir_name, f'Cover_{os.path.splitext(file_name)[0]}.jpg')
                run_ghostscript(tf2.name, out_fn)

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

        with tempfile.TemporaryDirectory() as tmp_dir_name, \
                tempfile.TemporaryDirectory(
                    dir=tmp_dir_name, prefix=f'PDF_Photos_{os.path.splitext(file_name)[0]}') as dir_name:

            # Convert the PDF file into photos
            run_ghostscript(tf.name, dir_name)
            shutil.make_archive(dir_name, 'zip', dir_name)

            # Send result file
            send_result_file(update, f'{dir_name}.sip')

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def run_ghostscript(in_fn, out_fn):
    """
    Run Ghostscript
    Args:
        in_fn: the string of the input file name
        out_fn: the string of the output file name

    Returns:
        None
    """
    args = ['pdf2png', '-dSAFER', '-sDEVICE=jpeg', '-o', out_fn, '-r300', in_fn]
    encoding = locale.getpreferredencoding()
    args = [a.encode(encoding) for a in args]
    ghostscript.Ghostscript(*args)


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
            with tempfile.TemporaryDirectory() as tmp_dir_name, \
                    tempfile.TemporaryDirectory(
                        dir=tmp_dir_name, prefix=f'Photos_{os.path.splitext(file_name)[0]}') as dir_name:
                # Find and store all photos
                log = Logger()
                for page in pdf_reader.pages:
                    if '/Resources' in page and '/XObject' in page['/Resources']:
                        x_object = page['/Resources']['/XObject'].getObject()

                        for obj in x_object:
                            if x_object[obj]['/Subtype'] == '/Image':
                                size = (x_object[obj]['/Width'], x_object[obj]['/Height'])
                                try:
                                    data = x_object[obj].getData()
                                except Exception:
                                    log.error(Exception)

                                    continue

                                if x_object[obj]['/ColorSpace'] == '/DeviceRGB':
                                    mode = 'RGB'
                                else:
                                    mode = 'P'

                                if x_object[obj]['/Filter'] == '/FlateDecode':
                                    try:
                                        img = Image.frombytes(mode, size, data)
                                        img.save(tempfile.NamedTemporaryFile(dir=dir_name, suffix='.png').name)
                                    except TypeError:
                                        pass
                                elif x_object[obj]['/Filter'] == '/DCTDecode':
                                    with open(tempfile.NamedTemporaryFile(
                                            dir=dir_name, suffix='.jpg').name, 'wb') as img:
                                        img.write(data)
                                elif x_object[obj]['/Filter'] == '/JPXDecode':
                                    with open(tempfile.NamedTemporaryFile(
                                            dir=dir_name, suffix='.jp2').name, 'wb') as img:
                                        img.write(data)

                if not os.listdir(dir_name):
                    update.message.reply_text('I couldn\'t find any photos in your PDF file.')
                else:
                    shutil.make_archive(dir_name, 'zip', dir_name)
                    send_result_file(update, f'{dir_name}.zip')

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
