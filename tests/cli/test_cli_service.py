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


@pytest.fixture(name="compress_command")
def fixture_compress_command(input_path: str, output_path: str) -> str:
    return (
        "gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 "
        "-dPDFSETTINGS=/default -dNOPAUSE -dQUIET -dBATCH "
        f"-sOutputFile={output_path} {input_path}"
    )


def test_compress_pdf(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
    compress_command: str,
):
    popen_process.returncode = 0
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        cli_service.compress_pdf(input_path, output_path)

        args = popen.call_args.args[0]
        assert " ".join(args) == compress_command


def test_compress_pdf_error(
    cli_service: CLIService,
    popen_process: Popen,
    input_path: str,
    output_path: str,
    compress_command: str,
):
    popen_process.returncode = 1
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process

        with pytest.raises(CLIServiceError):
            cli_service.compress_pdf(input_path, output_path)

        args = popen.call_args.args[0]
        assert " ".join(args) == compress_command
