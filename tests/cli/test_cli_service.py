from random import randint
from subprocess import Popen
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from pdf_bot.cli import CLIService, CLIServiceError


@pytest.fixture(name="cli_service")
def fixture_cli_service() -> CLIService:
    return CLIService()


@pytest.fixture(name="popen_process")
def fixture_popen_process() -> Popen:
    proc = cast(Popen, MagicMock())
    proc.communicate.return_value = ("0".encode("utf-8"), "1".encode("utf-8"))
    return proc


@pytest.fixture(name="input_path")
def fixture_input_path() -> str:
    return "input_path"


@pytest.fixture(name="output_path")
def fixture_output_path() -> str:
    return "output_path"


def test_compress_pdf(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
):
    popen_process.returncode = 0
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        cli_service.compress_pdf(input_path, output_path)

        args = popen.call_args.args[0]
        assert args[0] == "gs"
        assert input_path in args
        assert f"-sOutputFile={output_path}" in args


def test_compress_pdf_error(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
):
    popen_process.returncode = 1
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        with pytest.raises(CLIServiceError):
            cli_service.compress_pdf(input_path, output_path)


def test_crop_pdf_by_percentage(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
):
    percent = randint(0, 10)
    popen_process.returncode = 0

    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        cli_service.crop_pdf_by_percentage(input_path, output_path, percent)

        args = popen.call_args.args[0]
        assert args[0] == "pdf-crop-margins"
        assert input_path in args
        command = " ".join(args)
        assert f"-o {output_path}" in command
        assert f"-p {percent}" in command


def test_crop_pdf_by_percentage_error(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
):
    popen_process.returncode = 1
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        with pytest.raises(CLIServiceError):
            cli_service.crop_pdf_by_percentage(input_path, output_path, 0)


def test_crop_pdf_by_margin_size(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
):
    margin_size = randint(0, 10)
    popen_process.returncode = 0

    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        cli_service.crop_pdf_by_margin_size(input_path, output_path, margin_size)

        args = popen.call_args.args[0]
        assert args[0] == "pdf-crop-margins"
        assert input_path in args
        command = " ".join(args)
        assert f"-o {output_path}" in command
        assert f"-a {margin_size}" in command


def test_crop_pdf_by_margin_size_error(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
):
    popen_process.returncode = 1
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        with pytest.raises(CLIServiceError):
            cli_service.crop_pdf_by_margin_size(input_path, output_path, 0)
