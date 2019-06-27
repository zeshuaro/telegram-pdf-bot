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

from pdf_bot.constants import PDF_ID
from pdf_bot.utils import open_pdf, send_result


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
    if PDF_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PDF_ID]
    update.message.reply_text('Extracting a cover preview for your PDF file', reply_markup=ReplyKeyboardRemove())

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Cover_', suffix='.jpg'))
    file_name, tmp_file_name, out_file_name = [x.name for x in temp_files]

    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)

    pdf_reader = open_pdf(file_name, update)
    if pdf_reader:
        pdf_writer = PdfFileWriter()
        pdf_writer.addPage(pdf_reader.getPage(0))

        with open(tmp_file_name, 'wb') as f:
            pdf_writer.write(f)

        # Convert pdf to image
        run_ghostscript(tmp_file_name, out_file_name)
        send_result(update, out_file_name, 'cover preview')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    for tf in temp_files:
        tf.close()

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
    if PDF_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PDF_ID]
    update.message.reply_text('Converting your PDF file into photos', reply_markup=ReplyKeyboardRemove())

    # Setup temporary directory and files
    temp_dir = tempfile.TemporaryDirectory(prefix='PDF_Image_')
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    file_name = tf.name
    image_file_name = tempfile.NamedTemporaryFile(dir=image_dir, prefix='PDF_Image_', suffix='.jpg').name
    out_file_name = image_dir + '.zip'

    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)

    # Convert the PDF file
    run_ghostscript(file_name, image_file_name)
    shutil.make_archive(image_dir, 'zip', image_dir)
    send_result(update, out_file_name, 'photos of your', 'Here are the photos of your PDF file.')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    temp_dir.cleanup()
    tf.close()
    os.remove(out_file_name)

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
    if PDF_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PDF_ID]
    update.message.reply_text('Extracting all the photos in your PDF file', reply_markup=ReplyKeyboardRemove())

    # Setup temporary directory and file
    temp_dir = tempfile.TemporaryDirectory(prefix='Photos_')
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    file_name = tf.name
    out_file_name = image_dir + '.zip'

    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = open_pdf(file_name, update)

    if pdf_reader is not None:
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
            update.message.reply_text('I couldn\'t find any photos in your PDF file.')
        else:
            shutil.make_archive(image_dir, 'zip', image_dir)
            send_result(update, out_file_name, 'photos in your', 'Here are all the photos in your PDF file.')
            os.remove(out_file_name)

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    temp_dir.cleanup()
    tf.close()

    return ConversationHandler.END
