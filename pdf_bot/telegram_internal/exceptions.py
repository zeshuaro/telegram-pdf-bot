class TelegramServiceError(Exception):
    pass


class TelegramFileMimeTypeError(TelegramServiceError):
    pass


class TelegramFileTooLargeError(TelegramServiceError):
    pass


class TelegramGetUserDataError(TelegramServiceError):
    pass


class TelegramUpdateUserDataError(TelegramServiceError):
    pass


class TelegramImageNotFoundError(TelegramServiceError):
    pass
