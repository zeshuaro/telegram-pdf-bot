BOT_NAME = 'pdf2bot'
CHANNEL_NAME = 'pdf2botdev'

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

WAIT_COMPARE_FIRST = 0
WAIT_COMPARE_SECOND = 1

WAIT_MERGE = 0

WAIT_PHOTO = 0

WAIT_WATERMARK_SOURCE = 0
WAIT_WATERMARK = 1

PDF_OK = 0
PDF_INVALID_FORMAT = 1
PDF_TOO_LARGE = 2

CANCEL = 'cancel'
PDF_INFO = 'pdf_info'

PAYMENT = 'payment'
PAYMENT_PAYLOAD = 'payment_payload'
PAYMENT_CURRENCY = 'USD'
PAYMENT_PARA = 'payment_para'
PAYMENT_THANKS = 'Say Thanks 😁 ($1)'
PAYMENT_COFFEE = 'Coffee ☕ ($3)'
PAYMENT_BEER = 'Beer 🍺 ($5)'
PAYMENT_MEAL = 'Meal 🍲 ($10)'
PAYMENT_CUSTOM = 'Say Awesome 🤩 (Custom)'
WAIT_PAYMENT = 0

PAYMENT_DICT = {PAYMENT_THANKS: 1, PAYMENT_COFFEE: 3, PAYMENT_BEER: 5, PAYMENT_MEAL: 10}
