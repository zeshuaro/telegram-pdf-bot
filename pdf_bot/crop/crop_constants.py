import gettext

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext

BY_PERCENTAGE = _("By Percentage")
BY_MARGIN_SIZE = _("By Margin Size")

WAIT_CROP_TYPE = "wait_crop_type"
WAIT_CROP_PERCENTAGE = "wait_crop_percentage"
WAIT_CROP_MARGIN_SIZE = "wait_crop_margin_size"

MIN_PERCENTAGE = 0
MAX_PERCENTAGE = 100
