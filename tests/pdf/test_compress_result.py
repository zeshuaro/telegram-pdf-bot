from unittest.mock import patch

from pdf_bot.pdf import CompressResult
from tests.path_test_mixin import PathTestMixin


class TestCompressResult(PathTestMixin):
    def setup_method(self) -> None:
        path = self.mock_file_path()
        self.sut = CompressResult(29, 10, path)

    def test_reduced_percentage(self) -> None:
        actual = self.sut.reduced_percentage
        assert actual == 1 - self.sut.new_size / self.sut.old_size

    def test_readable_old_size(self) -> None:
        with patch("pdf_bot.pdf.models.humanize") as humanize:
            _ = self.sut.readable_old_size
            humanize.naturalsize.assert_called_once_with(self.sut.old_size)

    def test_readable_new_size(self) -> None:
        with patch("pdf_bot.pdf.models.humanize") as humanize:
            _ = self.sut.readable_new_size
            humanize.naturalsize.assert_called_once_with(self.sut.new_size)
