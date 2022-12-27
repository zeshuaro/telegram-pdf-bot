class TelegramServiceError(Exception):
    ...


class TelegramFileMimeTypeError(TelegramServiceError):
    ...


class TelegramFileTooLargeError(TelegramServiceError):
    ...


class TelegramGetUserDataError(TelegramServiceError):
    ...


class TelegramImageNotFoundError(TelegramServiceError):
    ...
