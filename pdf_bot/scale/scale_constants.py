import gettext

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext

BY_SCALING_FACTOR = _("By scaling factor")
TO_DIMENSION = _("To dimension")

WAIT_SCALE_TYPE = "wait_scale_type"
WAIT_SCALE_FACTOR = "wait_scale_factor"
WAIT_SCALE_DIMENSION = "wait_scale_dimension"
