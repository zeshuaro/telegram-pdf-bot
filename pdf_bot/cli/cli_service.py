import gettext
import shlex
from subprocess import PIPE, Popen

from loguru import logger

from pdf_bot.cli.exceptions import CLINonZeroExitStatusError

_ = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"]).gettext


class CLIService:
    @staticmethod
    def run_command(command: str):
        proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE, shell=False)
        out, err = proc.communicate()

        if proc.returncode != 0:
            logger.error(
                f"Command:\n{command}\n\n"
                f'Stdout:\n{out.decode("utf-8")}\n\n'
                f'Stderr:\n{err.decode("utf-8")}'
            )
            raise CLINonZeroExitStatusError(_("Failed to complete process"))
