import os
import re
import shlex
import shutil
import tempfile
import wand.image

from logbook import Logger
from PIL import Image as PillowImage
from PyPDF2 import PdfFileWriter, PdfFileReader
from subprocess import Popen, PIPE
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from constants import WAIT_TASK, WAIT_DECRYPT_PW, WAIT_ENCRYPT_PW, WAIT_ROTATE_DEGREE, WAIT_SCALE_BY_X, \
    WAIT_SCALE_BY_Y, WAIT_SCALE_TO_X, WAIT_SCALE_TO_Y, WAIT_SPLIT_RANGE, WAIT_FILE_NAME
from utils import cancel, open_pdf, send_result, process_pdf
from crypto import ask_decrypt_pw, ask_encrypt_pw, decrypt_pdf, encrypt_pdf
from photo import process_photo
from scale import ask_scale_x, ask_scale_by_y, ask_scale_to_y, pdf_scale_by, pdf_scale_to

PDF_ID = 'pdf_id'
PHOTO_ID = 'photo_id'


def file_cov_handler():
    """
    Create the file conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.document, check_doc, pass_user_data=True),
                      MessageHandler(Filters.photo, check_photo, pass_user_data=True)],
        states={
            WAIT_TASK: [MessageHandler(Filters.regex('^Cover$'), get_pdf_cover, pass_user_data=True),
                        MessageHandler(Filters.regex('^Decrypt$'), ask_decrypt_pw),
                        MessageHandler(Filters.regex('^Encrypt$'), ask_encrypt_pw),
                        MessageHandler(Filters.regex('^Extract Images$'), get_pdf_img, pass_user_data=True),
                        MessageHandler(Filters.regex('^To Images$'), pdf_to_img, pass_user_data=True),
                        MessageHandler(Filters.regex('^Rotate$'), ask_rotate_degree),
                        MessageHandler(Filters.regex('^Scale By$'), ask_scale_x),
                        MessageHandler(Filters.regex('^Scale To$'), ask_scale_x),
                        MessageHandler(Filters.regex('^Split$'), ask_split_range),
                        MessageHandler(Filters.regex('^(Beautify|Convert)$'), receive_photo_task, pass_user_data=True),
                        MessageHandler(Filters.regex('^Rename$'), ask_pdf_new_name)],
            WAIT_DECRYPT_PW: [MessageHandler(Filters.text, decrypt_pdf, pass_user_data=True)],
            WAIT_ENCRYPT_PW: [MessageHandler(Filters.text, encrypt_pdf, pass_user_data=True)],
            WAIT_ROTATE_DEGREE: [MessageHandler('^(90|180|270)$', rotate_pdf, pass_user_data=True)],
            WAIT_SCALE_BY_X: [MessageHandler(Filters.text, ask_scale_by_y, pass_user_data=True)],
            WAIT_SCALE_BY_Y: [MessageHandler(Filters.text, pdf_scale_by, pass_user_data=True)],
            WAIT_SCALE_TO_X: [MessageHandler(Filters.text, ask_scale_to_y, pass_user_data=True)],
            WAIT_SCALE_TO_Y: [MessageHandler(Filters.text, pdf_scale_to, pass_user_data=True)],
            WAIT_SPLIT_RANGE: [MessageHandler(Filters.text, split_pdf, pass_user_data=True)],
            WAIT_FILE_NAME: [MessageHandler(Filters.text, rename_pdf, pass_user_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler('^Cancel$', cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def check_doc(update, _, user_data):
    """
    Validate the document and wait for the next action
    Args:
        update: the update object
        _: unused variable
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for the next action or the conversation has ended
    """
    doc = update.message.document
    mime_type = doc.mime_type

    if mime_type.startswith('image'):
        return check_photo(update, _, user_data, doc)
    elif not mime_type.endswith('pdf'):
        return ConversationHandler.END
    elif doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text('The PDF file you sent is too large for me to download. '
                                  'Sorry that I can\'t perform any tasks on your PDF file.')

        return ConversationHandler.END

    user_data[PDF_ID] = doc.file_id
    keywords = sorted(['Decrypt', 'Encrypt', 'Rotate', 'Scale By', 'Scale To', 'Split', 'Cover', 'To Images',
                       'Extract Images', 'Rename'])
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append(['Cancel'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Please select the task that you\'ll like to perform.', reply_markup=reply_markup)

    return WAIT_TASK


@run_async
def check_photo(update, _, user_data, photo_file=None):
    """
    Validate the photo and wait for the next action
    Args:
        update: the update object
        _: unused variable
        user_data: the dict of user data
        photo_file: the photo file object

    Returns:
        The variable indicating to wait for the next action or the conversation has ended
    """
    if photo_file is None:
        photo_file = update.message.photo[-1]

    if photo_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        update.message.reply_text('The photo you sent is too large for me to download. '
                                  'Sorry that I can\'t beautify and convert your photo.')

        return ConversationHandler.END

    user_data[PHOTO_ID] = photo_file.file_id
    keyboard = [['Beautify', 'Convert'], ['Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Please select the task that you\'ll like to perform.', reply_markup=reply_markup)

    return WAIT_TASK


@run_async
def receive_photo_task(update, context, user_data):
    """
    Receive the task and perform the task on the photo
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
    if PHOTO_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PHOTO_ID]
    if update.message.text.lower() == 'beautify':
        process_photo(update, context, [file_id], is_beautify=True)
    else:
        process_photo(update, context, [file_id], is_beautify=False)

    if user_data[PHOTO_ID] == file_id:
        del user_data[PHOTO_ID]

    return ConversationHandler.END


@run_async
def get_pdf_cover(update, context, user_data):
    """
    Get the PDF cover page in JPEG format
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
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

        with wand.image.Image(filename=tmp_file_name, resolution=300) as img:
            with img.convert('jpg') as converted:
                converted.save(filename=out_file_name)

        send_result(update, out_file_name, 'cover preview')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


@run_async
def get_pdf_img(update, context, user_data):
    """
    Get all the images in the PDF file
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
    if PDF_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PDF_ID]
    update.message.reply_text('Extracting all the images in your PDF file', reply_markup=ReplyKeyboardRemove())

    # Setup temporary directory and file
    temp_dir = tempfile.TemporaryDirectory(prefix='Images_')
    image_dir = temp_dir.name
    tf = tempfile.NamedTemporaryFile()
    file_name = tf.name
    out_file_name = image_dir + '.zip'

    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = open_pdf(file_name, update)

    if pdf_reader is not None:
        # Find and store all images
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
            send_result(update, out_file_name, 'images in your', 'Here are all the images in your PDF file.')
            os.remove(out_file_name)

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    temp_dir.cleanup()
    tf.close()

    return ConversationHandler.END


@run_async
def pdf_to_img(update, context, user_data):
    """
    Convert the PDF file into JPEG photos
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
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
    with wand.image.Image(filename=file_name, resolution=300) as img:
        with img.convert('jpg') as converted:
            converted.save(filename=image_file_name)

    shutil.make_archive(image_dir, 'zip', image_dir)
    send_result(update, out_file_name, 'images of your', 'Here are the images of your PDF file.')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    temp_dir.cleanup()
    tf.close()
    os.remove(out_file_name)

    return ConversationHandler.END


@run_async
def ask_pdf_new_name(update, _):
    """
    Ask and wait for the new file name
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the file name
    """
    update.message.reply_text('Please send me the file name that you\'ll like to rename your PDF file into.',
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_FILE_NAME


@run_async
def rename_pdf(update, context, user_data):
    """
    Rename the PDF file with the given file name
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for the file name or the conversation has ended
    """
    if PDF_ID not in user_data:
        return ConversationHandler.END

    text = re.sub(r'\.pdf$', '', update.message.text)
    invalid_chars = r'\/*?:\'<>|'
    if set(text) & set(invalid_chars):
        update.message.reply_text(f'File names can\'t contain any of the following characters:\n{invalid_chars}\n'
                                  f'Please try again.')

        return WAIT_FILE_NAME

    file_id = user_data[PDF_ID]
    new_name = '{}.pdf'.format(text)
    update.message.reply_text(f'Renaming your PDF file into *{new_name}*...', parse_mode='Markdown')

    # Setup temporary directory and file
    temp_file = tempfile.NamedTemporaryFile()
    temp_dir = tempfile.TemporaryDirectory()
    file_name = temp_file.name

    # Download PDF file
    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)

    new_file_name = '{}/{}'.format(temp_dir.name, new_name)
    shutil.move(file_name, new_file_name)
    send_result(update, new_file_name, 'renamed')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    temp_dir.cleanup()
    try:
        temp_file.close()
    except FileNotFoundError:
        pass

    return ConversationHandler.END


@run_async
def ask_rotate_degree(update, _):
    """
    Ask and wait for the rotation degree
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the rotation degree
    """
    keyboard = [['90'], ['180'], ['270']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Please select the degrees that you\'ll like to rotate your PDF file in clockwise.',
                              reply_markup=reply_markup)

    return WAIT_ROTATE_DEGREE


@run_async
def rotate_pdf(update, context, user_data):
    """
    Rotate the PDF file with the given rotation degree
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The vairable indicating the conversation has ended
    """
    if PDF_ID not in user_data:
        return ConversationHandler.END

    degree = int(update.message.text)
    update.message.reply_text(f'Rotating your PDF file clockwise by {degree} degrees',
                              reply_markup=ReplyKeyboardRemove())
    process_pdf(update, context, user_data, 'rotated', rotate_degree=degree)

    return ConversationHandler.END


@run_async
def ask_split_range(update, _):
    """
    Ask and wait for the split page range
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the split page range
    """
    update.message.reply_text('Please send me the range of pages that you will like to keep. You can use ⚡ *INSTANT '
                              'VIEW* from below or refer to [here](http://telegra.ph/Telegram-PDF-Bot-07-16) for '
                              'some range examples.', parse_mode='markdown', reply_markup=ReplyKeyboardRemove())

    return WAIT_SPLIT_RANGE


@run_async
def split_pdf(update, context, user_data):
    """
    Split the PDF file with the given split page range
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for the split page range or the conversation has ended
    """
    if PDF_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PDF_ID]
    split_range = update.message.text
    update.message.reply_text('Splitting your PDF file...')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix='Split_', suffix='.pdf')]
    file_name, out_file_name = [x.name for x in temp_files]

    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = open_pdf(file_name, update)

    if pdf_reader:
        command = 'python3 pdfcat.py -o {out_file_name} {in_file_name} {split_range}'. \
            format(out_file_name=out_file_name, in_file_name=file_name, split_range=split_range)

        proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
        proc_out, proc_err = proc.communicate()

        if proc.returncode != 0 or not os.path.exists(out_file_name):
            log = Logger()
            log.error(proc_err.decode('utf8'))
            update.message.reply_text('Something went wrong, please try again.')

            return ConversationHandler.END

        reader = PdfFileReader(out_file_name)
        if reader.getNumPages() == 0:
            for tf in temp_files:
                tf.close()
            update.message.reply_text('The range is invalid. Please send me the range again.')

            return WAIT_SPLIT_RANGE

        send_result(update, out_file_name, 'split')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
