from unittest.mock import patch

from pdf_bot.pdf import CompressResult


class TestCompressResult:
    SUT = CompressResult(29, 10, "out_path")

    def test_reduced_percentage(self) -> None:
        actual = self.SUT.reduced_percentage
        assert actual == 1 - self.SUT.new_size / self.SUT.old_size

    def test_readable_old_size(self) -> None:
        with patch("pdf_bot.pdf.models.humanize") as humanize:
            _ = self.SUT.readable_old_size
            humanize.naturalsize.assert_called_once_with(self.SUT.old_size)

    def test_readable_new_size(self) -> None:
        with patch("pdf_bot.pdf.models.humanize") as humanize:
            _ = self.SUT.readable_new_size
            humanize.naturalsize.assert_called_once_with(self.SUT.new_size)
