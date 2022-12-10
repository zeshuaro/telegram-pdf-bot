class FeedbackServiceError(Exception):
    pass


class FeedbackInvalidLanguageError(FeedbackServiceError):
    pass
