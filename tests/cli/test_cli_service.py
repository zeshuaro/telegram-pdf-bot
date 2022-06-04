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


def test_run_command(cli_service: CLIService, popen_process: Popen):
    popen_process.returncode = 0
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process
        cli_service.run_command("command")


def test_run_command_error(cli_service: CLIService, popen_process: Popen):
    popen_process.returncode = 1
    with patch("pdf_bot.cli.cli_service.Popen") as popen:
        popen.return_value = popen_process
        with pytest.raises(CLIServiceError):
            cli_service.run_command("cd")
