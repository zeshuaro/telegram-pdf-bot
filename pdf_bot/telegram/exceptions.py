class TelegramServiceError(Exception):
    pass


class TelegramFileMimeTypeError(TelegramServiceError):
    pass


class TelegramFileTooLargeError(TelegramServiceError):
    pass


class TelegramUserDataKeyError(TelegramServiceError):
    pass
