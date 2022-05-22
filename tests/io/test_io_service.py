import os

import pytest

from pdf_bot.io import IOService


@pytest.fixture(name="io_service")
def fixture_io_service() -> IOService:
    return IOService()


def test_create_temp_file_with_prefix(io_service: IOService):
    prefix = "prefix"
    with io_service.create_temp_file(prefix=prefix) as out_path:
        paths = os.path.split(out_path)
        assert paths[1].startswith(prefix)


def test_create_temp_file_with_suffix(io_service: IOService):
    suffix = "suffix"
    with io_service.create_temp_file(suffix=suffix) as out_path:
        paths = os.path.split(out_path)
        assert paths[1].endswith(suffix)


def test_create_temp_pdf_file(io_service: IOService):
    with io_service.create_temp_pdf_file("prefix") as out_path:
        paths = os.path.split(out_path)
        assert paths[1].endswith(".pdf")


def test_create_temp_png_file(io_service: IOService):
    with io_service.create_temp_png_file("prefix") as out_path:
        paths = os.path.split(out_path)
        assert paths[1].endswith(".png")
