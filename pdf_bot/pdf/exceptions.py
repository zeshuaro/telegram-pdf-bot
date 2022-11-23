class PdfServiceError(Exception):
    pass


class PdfReadError(PdfServiceError):
    pass


class PdfEncryptError(PdfServiceError):
    pass


class PdfDecryptError(PdfServiceError):
    pass


class PdfIncorrectPasswordError(PdfServiceError):
    pass


class PdfOcrError(PdfServiceError):
    pass


class PdfNoTextError(PdfServiceError):
    pass


class PdfNoImagesError(PdfServiceError):
    pass
