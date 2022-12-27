class TelegramServiceError(Exception):
    ...


class TelegramFileMimeTypeError(TelegramServiceError):
    ...


class TelegramFileTooLargeError(TelegramServiceError):
    ...


class TelegramGetUserDataError(TelegramServiceError):
    ...


class TelegramUpdateUserDataError(TelegramServiceError):
    ...


class TelegramImageNotFoundError(TelegramServiceError):
    ...
