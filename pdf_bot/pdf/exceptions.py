from gettext import gettext as _


class PdfServiceError(Exception):
    pass


class PdfReadError(PdfServiceError):
    pass


class PdfDecryptError(PdfServiceError):
    pass


class PdfIncorrectPasswordError(PdfServiceError):
    pass


class PdfNoTextError(PdfServiceError):
    pass


class PdfNoImagesError(PdfServiceError):
    pass


class PdfEncryptedError(PdfServiceError):
    _MESSAGE = _("Your PDF file is encrypted, decrypt it first then try again")

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(self._MESSAGE, *args, **kwargs)
