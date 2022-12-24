import os
from contextlib import contextmanager
from typing import Generator

import img2pdf
import noteshrink

from pdf_bot.cli import CLIService
from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import TelegramService


class ImageService:
    def __init__(
        self,
        cli_service: CLIService,
        io_service: IOService,
        telegram_service: TelegramService,
    ) -> None:
        self.cli_service = cli_service
        self.io_service = io_service
        self.telegram_service = telegram_service

    @contextmanager
    def beautify_and_convert_images_to_pdf(
        self, file_data_list: list[FileData]
    ) -> Generator[str, None, None]:
        file_ids = self._get_file_ids(file_data_list)
        with self.telegram_service.download_files(
            file_ids
        ) as file_paths, self.io_service.create_temp_pdf_file("Beautified") as out_path:
            out_path_base = os.path.splitext(out_path)[0]
            noteshrink.notescan_main(
                file_paths, basename=f"{out_path_base}_page", pdfname=out_path
            )
            yield out_path

    @contextmanager
    def convert_images_to_pdf(
        self, file_data_list: list[FileData]
    ) -> Generator[str, None, None]:
        file_ids = self._get_file_ids(file_data_list)
        with self.telegram_service.download_files(
            file_ids
        ) as file_paths, self.io_service.create_temp_pdf_file("Converted") as out_path:
            with open(out_path, "wb") as f:
                f.write(img2pdf.convert(file_paths))
            yield out_path

    @staticmethod
    def _get_file_ids(file_data_list: list[FileData]) -> list[str]:
        return [x.file_id for x in file_data_list]
