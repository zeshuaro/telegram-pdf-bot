class TelegramServiceError(Exception):
    pass


class TelegramFileMimeTypeError(TelegramServiceError):
    pass


class TelegramFileTooLargeError(TelegramServiceError):
    pass
