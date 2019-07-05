# Bot constants
BOT_NAME = 'pdf2bot'
CHANNEL_NAME = 'pdf2botdev'
TIMEOUT = 20
MAX_MEDIA_GROUP = 10

# Compare constants
WAIT_COMPARE_FIRST = 0
WAIT_COMPARE_SECOND = 1

# Merge constants
WAIT_MERGE = 0

# Watermark constants
WAIT_WATERMARK_SOURCE = 0
WAIT_WATERMARK = 1

# File constants
WAIT_TASK = 0
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
WAIT_PHOTO_TYPE = 13

# Photo constants
WAIT_PHOTO = 0

# PDF file validation constants
PDF_OK = 0
PDF_INVALID_FORMAT = 1
PDF_TOO_LARGE = 2

# Keyboard Constants
CANCEL = 'Cancel'
DONE = 'Done'
BACK = 'Back'
CROP_PERCENT = 'By Percentage'
CROP_SIZE = 'By Margin Size'
COVER = 'Cover'
DECRYPT = 'Decrypt'
ENCRYPT = 'Encrypt'
EXTRACT_IMG = 'Extract Photos'
TO_IMG = 'To Photos'
ROTATE = 'Rotate'
SCALE_BY = 'Scale By'
SCALE_TO = 'Scale To'
SPLIT = 'Split'
BEAUTIFY = 'Beautify'
CONVERT = 'Convert'
RENAME = 'Rename'
CROP = 'Crop'
ROTATE_90 = '90'
ROTATE_180 = '180'
ROTATE_270 = '270'
ZIPPED = 'Zipped'
PHOTOS = 'Photos'

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

# GCP constants
USER = 'User'
COUNT = 'count'
