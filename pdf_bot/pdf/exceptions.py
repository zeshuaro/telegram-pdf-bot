class PdfServiceError(Exception):
    pass


class PdfReadError(PdfServiceError):
    pass


class PdfEncryptError(PdfServiceError):
    pass


class PdfDecryptError(PdfServiceError):
    pass
