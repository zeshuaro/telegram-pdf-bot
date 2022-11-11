import gettext
import shlex
from subprocess import PIPE, Popen

from loguru import logger

from pdf_bot.cli.exceptions import CLINonZeroExitStatusError

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


class CLIService:
    def compress_pdf(self, input_path: str, output_path: str) -> None:
        command = (
            "gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/default "
            f'-dNOPAUSE -dQUIET -dBATCH -sOutputFile="{output_path}" "{input_path}"'
        )
        self._run_command(command)

    def crop_pdf_by_percentage(
        self, input_path: str, output_path: str, percentage: float
    ) -> None:
        self._crop_pdf(input_path, output_path, percentage=percentage)

    def crop_pdf_by_margin_size(
        self, input_path: str, output_path: str, margin_size: float
    ) -> None:
        self._crop_pdf(input_path, output_path, margin_size=margin_size)

    def _crop_pdf(
        self,
        input_path: str,
        output_path: str,
        percentage: float | None = None,
        margin_size: float | None = None,
    ) -> None:
        command = f'pdf-crop-margins -o "{output_path}" "{input_path}"'
        if percentage is not None:
            command += f" -p {percentage}"
        else:
            command += f" -a {margin_size}"
        self._run_command(command)

    @staticmethod
    def _run_command(command: str) -> None:
        proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE, shell=False)
        out, err = proc.communicate()

        if proc.returncode != 0:
            logger.error(
                f"Command:\n{command}\n\n"
                f'Stdout:\n{out.decode("utf-8")}\n\n'
                f'Stderr:\n{err.decode("utf-8")}'
            )
            raise CLINonZeroExitStatusError(_("Failed to complete process"))
