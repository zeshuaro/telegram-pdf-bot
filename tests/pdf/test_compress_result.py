from random import randint
from unittest.mock import patch

import pytest

from pdf_bot.pdf import CompressResult


@pytest.fixture(name="compress_result")
def fixture_compress_result():
    return CompressResult(randint(11, 20), randint(1, 10), "out_path")


def test_reduced_percentage(compress_result: CompressResult):
    actual = compress_result.reduced_percentage
    assert actual == 1 - compress_result.new_size / compress_result.old_size


def test_readable_old_size(compress_result: CompressResult):
    with patch("pdf_bot.pdf.models.humanize") as humanize:
        _ = compress_result.readable_old_size
        humanize.naturalsize.assert_called_once_with(compress_result.old_size)


def test_readable_new_size(compress_result: CompressResult):
    with patch("pdf_bot.pdf.models.humanize") as humanize:
        _ = compress_result.readable_new_size
        humanize.naturalsize.assert_called_once_with(compress_result.new_size)
