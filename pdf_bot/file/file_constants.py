import gettext

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext

PREVIEW = _("Preview")
DECRYPT = _("Decrypt")
ENCRYPT = _("Encrypt")
EXTRACT_IMAGE = _("Extract Images")
TO_IMAGES = _("To Images")
ROTATE = _("Rotate")
SCALE = _("Scale")
SPLIT = _("Split")
BEAUTIFY = _("Beautify")
TO_PDF = _("To PDF")
RENAME = _("Rename")
CROP = _("Crop")
COMPRESSED = _("Compressed")
IMAGES = _("Images")
REMOVE_LAST = _("Remove Last File")
TO_DIMENSIONS = _("To Dimensions")
EXTRACT_TEXT = _("Extract Text")
TEXT_MESSAGE = _("Text Message")
TEXT_FILE = _("Text File")
OCR = "OCR"
COMPRESS = _("Compress")
BLACK_AND_WHITE = _("Black & White")

WAIT_PDF_TASK = "wait_pdf_task"

PDF_TASKS = sorted(
    [
        DECRYPT,
        ENCRYPT,
        ROTATE,
        SCALE,
        SPLIT,
        PREVIEW,
        TO_IMAGES,
        EXTRACT_IMAGE,
        RENAME,
        CROP,
        EXTRACT_TEXT,
        OCR,
        COMPRESS,
        BLACK_AND_WHITE,
    ]
)
