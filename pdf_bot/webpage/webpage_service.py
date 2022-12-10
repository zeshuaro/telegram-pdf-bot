from contextlib import contextmanager
from gettext import gettext as _
from typing import Generator
from urllib.parse import urlparse

from weasyprint import HTML
from weasyprint.urls import URLFetchingError

from pdf_bot.io import IOService

from .exceptions import WebpageServiceError


class WebpageService:
    def __init__(self, io_service: IOService) -> None:
        self.io_service = io_service

    @contextmanager
    def url_to_pdf(self, url: str) -> Generator[str, None, None]:
        o = urlparse(url)
        with self.io_service.create_temp_pdf_file(o.hostname) as out_path:
            try:
                HTML(url=url).write_pdf(out_path)
                yield out_path
            except URLFetchingError as e:
                raise WebpageServiceError(_("Unable to reach your web page")) from e
            except AssertionError as e:
                raise WebpageServiceError(_("Failed to convert your web page")) from e
