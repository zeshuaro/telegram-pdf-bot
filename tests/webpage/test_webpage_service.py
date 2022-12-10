from unittest.mock import MagicMock, patch

import pytest
from weasyprint import HTML
from weasyprint.urls import URLFetchingError

from pdf_bot.io import IOService
from pdf_bot.webpage import WebpageService, WebpageServiceError


class TestWebpageService:
    URL = "https://example.com"
    FILE_PATH = "file_path"

    def setup_method(self) -> None:
        self.io_service = MagicMock(spec=IOService)
        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        self.sut = WebpageService(self.io_service)

        self.html = MagicMock(spec=HTML)
        self.html_cls_patcher = patch(
            "pdf_bot.webpage.webpage_service.HTML", return_value=self.html
        )
        self.html_cls = self.html_cls_patcher.start()

    def teardown_method(self) -> None:
        self.html_cls_patcher.stop()

    def test_url_to_pdf(self) -> None:
        with self.sut.url_to_pdf(self.URL) as actual:
            assert actual == self.FILE_PATH
            self._assert_io_service_and_html()

    @pytest.mark.parametrize("exception", [URLFetchingError(), AssertionError()])
    def test_url_to_pdf_error(self, exception: Exception) -> None:
        self.html.write_pdf.side_effect = exception
        with pytest.raises(WebpageServiceError), self.sut.url_to_pdf(self.URL):
            self._assert_io_service_and_html()

    def _assert_io_service_and_html(self) -> None:
        self.io_service.create_temp_pdf_file.assert_called_once_with("example.com")
        self.html_cls.assert_called_once_with(url=self.URL)
        self.html.write_pdf.assert_called_once_with(self.FILE_PATH)
