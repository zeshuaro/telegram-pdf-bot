import gettext

t = gettext.translation('pdf_bot', localedir='locale', languages=['en'])
_ = t.gettext

# Bot constants
CHANNEL_NAME = 'pdf2botdev'

# PDF file validation constants
PDF_OK = 0
PDF_INVALID_FORMAT = 1
PDF_TOO_LARGE = 2

# PDF file constants
WAIT_DOC_TASK = 0
WAIT_DECRYPT_PW = 1
WAIT_ENCRYPT_PW = 2
WAIT_ROTATE_DEGREE = 3
WAIT_SCALE_BY_X = 4
WAIT_SCALE_BY_Y = 5
WAIT_SCALE_TO_X = 6
WAIT_SCALE_TO_Y = 7
WAIT_SPLIT_RANGE = 8
WAIT_FILE_NAME = 9
WAIT_CROP_TYPE = 10
WAIT_CROP_PERCENT = 11
WAIT_CROP_OFFSET = 12
WAIT_EXTRACT_PHOTO_TYPE = 13
WAIT_TO_PHOTO_TYPE = 14
WAIT_PHOTO_TASK = 15

# Keyboard constants
CANCEL = _('Cancel')
DONE = _('Done')
BACK = _('Back')
CROP_PERCENT = _('By Percentage')
CROP_SIZE = _('By Margin Size')
PREVIEW = _('Preview')
DECRYPT = _('Decrypt')
ENCRYPT = _('Encrypt')
EXTRACT_IMG = _('Extract Photos')
TO_IMG = _('To Photos')
ROTATE = _('Rotate')
SCALE_BY = _('Scale By')
SCALE_TO = _('Scale To')
SPLIT = _('Split')
BEAUTIFY = _('Beautify')
CONVERT = _('Convert')
RENAME = _('Rename')
CROP = _('Crop')
ZIPPED = _('Zipped')
PHOTOS = _('Photos')

# Rotation constants
ROTATE_90 = '90'
ROTATE_180 = '180'
ROTATE_270 = '270'

# User data constants
PDF_INFO = 'pdf_info'

# Payment Constants
PAYMENT = 'payment'
PAYMENT_PAYLOAD = 'payment_payload'
PAYMENT_CURRENCY = 'USD'
PAYMENT_PARA = 'payment_para'
PAYMENT_THANKS = 'Say Thanks 😁 ($1)'
PAYMENT_COFFEE = 'Coffee ☕ ($3)'
PAYMENT_BEER = 'Beer 🍺 ($5)'
PAYMENT_MEAL = 'Meal 🍲 ($10)'
PAYMENT_CUSTOM = 'Say Awesome 🤩 (Custom)'
PAYMENT_DICT = {PAYMENT_THANKS: 1, PAYMENT_COFFEE: 3, PAYMENT_BEER: 5, PAYMENT_MEAL: 10}
WAIT_PAYMENT = 0

# Datastore constants
USER = 'User'
COUNT = 'count'
LANGUAGE = 'language'
