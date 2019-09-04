import gettext

t = gettext.translation('pdf_bot', localedir='locale', languages=['en_UK'])
_ = t.gettext

# Bot constants
CHANNEL_NAME = 'pdf2botdev'
SET_LANG = 'set_lang'

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
CURRENCY = 'USD'
PAYMENT_PARA = 'payment_para'
THANKS = _('Say Thanks 😁 ($1)')
COFFEE = _('Coffee ☕ ($3)')
BEER = _('Beer 🍺 ($5)')
MEAL = _('Meal 🍲 ($10)')
CUSTOM = _('Say Awesome 🤩 (Custom)')
PAYMENT_DICT = {THANKS: 1, COFFEE: 3, BEER: 5, MEAL: 10}
CUSTOM_MSG = _('Send me the amount that you\'ll like to support PDF Bot')
WAIT_PAYMENT = 0

# Datastore constants
USER = 'User'
COUNT = 'count'
LANGUAGE = 'language'

# Language constants
LANGUAGES = {'🇬🇧 English': 'en_UK', '🇭🇰 廣東話': 'zh_HK', '🇹🇼 繁體中文': 'zh_TW', '🇨🇳 简体中文': 'zh_CN'}
