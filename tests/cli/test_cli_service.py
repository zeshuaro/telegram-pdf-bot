import shlex
from subprocess import Popen
from unittest.mock import MagicMock, patch

import pytest

from pdf_bot.cli import CLIService, CLIServiceError


class TestCLIService:
    @classmethod
    def setup_class(cls) -> None:
        cls.input_path = "input_path"
        cls.output_path = "output_path"
        cls.percent = 0.1
        cls.margin_size = 10

    def setup_method(self) -> None:
        self.process = MagicMock(spec=Popen)
        self.process.communicate.return_value = (
            "0".encode("utf-8"),
            "1".encode("utf-8"),
        )

        self.popen_patcher = patch(
            "pdf_bot.cli.cli_service.Popen", return_value=self.process
        )
        self.popen = self.popen_patcher.start()

        self.sut = CLIService()

    def teardown_method(self) -> None:
        self.popen_patcher.stop()

    def test_compress_pdf(self) -> None:
        self.process.returncode = 0
        self.sut.compress_pdf(self.input_path, self.output_path)
        self._assert_compress_command()

    def test_compress_pdf_error(self) -> None:
        self.process.returncode = 1

        with pytest.raises(CLIServiceError):
            self.sut.compress_pdf(self.input_path, self.output_path)

        self._assert_compress_command()

    def test_crop_pdf_by_percentage(self) -> None:
        self.process.returncode = 0
        self.sut.crop_pdf_by_percentage(self.input_path, self.output_path, self.percent)
        self._assert_crop_pdf_percentage_command()

    def test_crop_pdf_by_percentage_error(self) -> None:
        self.process.returncode = 1

        with pytest.raises(CLIServiceError):
            self.sut.crop_pdf_by_percentage(
                self.input_path, self.output_path, self.percent
            )

        self._assert_crop_pdf_percentage_command()

    def test_crop_pdf_by_margin_size(self) -> None:
        self.process.returncode = 0
        self.sut.crop_pdf_by_margin_size(
            self.input_path, self.output_path, self.margin_size
        )
        self._assert_crop_pdf_margin_size_command()

    def test_crop_pdf_by_margin_size_error(self) -> None:
        self.process.returncode = 1

        with pytest.raises(CLIServiceError):
            self.sut.crop_pdf_by_margin_size(
                self.input_path, self.output_path, self.margin_size
            )

        self._assert_crop_pdf_margin_size_command()

    def _assert_compress_command(self) -> None:
        args = self.popen.call_args.args[0]
        assert args == shlex.split(
            "gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/default "
            f'-dNOPAUSE -dQUIET -dBATCH -sOutputFile="{self.output_path}" '
            f'"{self.input_path}"'
        )

    def _assert_crop_pdf_percentage_command(self) -> None:
        args = self.popen.call_args.args[0]
        assert args == shlex.split(
            f'pdf-crop-margins -o "{self.output_path}" "{self.input_path}" '
            f"-p {self.percent}"
        )

    def _assert_crop_pdf_margin_size_command(self) -> None:
        args = self.popen.call_args.args[0]
        assert args == shlex.split(
            f'pdf-crop-margins -o "{self.output_path}" "{self.input_path}" '
            f"-a {self.margin_size}"
        )
