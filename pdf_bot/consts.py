from gettext import gettext as _

from telegram.ext import filters

TEXT_FILTER = filters.TEXT & ~filters.COMMAND

# Bot constants
CHANNEL_NAME = "pdf2botdev"

# Keyboard constants
CANCEL = _("Cancel")
DONE = _("Done")
BACK = _("Back")

# User data constants
FILE_DATA = "file_data"
MESSAGE_DATA = "message_data"

# Datastore constants
USER = "User"
LANGUAGE = "language"
