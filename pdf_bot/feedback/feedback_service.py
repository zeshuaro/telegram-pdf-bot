from gettext import gettext as _

from langdetect import detect

from .exceptions import FeedbackInvalidLanguageError
from .feedback_repository import FeedbackRepository


class FeedbackService:
    _VALID_LANGUAGE_CODE = "en"

    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self.feedback_repository = feedback_repository

    def save_feedback(self, chat_id: str, username: str, feedback: str) -> None:
        feedback_lang = detect(feedback)
        if feedback_lang.lower() == self._VALID_LANGUAGE_CODE:
            self.feedback_repository.save_feedback(chat_id, username, feedback)
        else:
            raise FeedbackInvalidLanguageError(
                _("The feedback is not in English, try again")
            )
