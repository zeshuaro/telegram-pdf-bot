from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import img2pdf
import noteshrink
from img2pdf import Rotation

from pdf_bot.cli import CLIService
from pdf_bot.io_internal import IOService
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

    @asynccontextmanager
    async def beautify_and_convert_images_to_pdf(
        self, file_data_list: list[FileData]
    ) -> AsyncGenerator[Path, None]:
        file_ids = self._get_file_ids(file_data_list)
        async with self.telegram_service.download_files(file_ids) as file_paths:
            with self.io_service.create_temp_pdf_file("Beautified") as out_path:
                noteshrink.notescan_main(
                    file_paths, basename=f"{out_path.stem}_page", pdfname=out_path
                )
                yield out_path

    @asynccontextmanager
    async def convert_images_to_pdf(
        self, file_data_list: list[FileData]
    ) -> AsyncGenerator[Path, None]:
        file_ids = self._get_file_ids(file_data_list)
        async with self.telegram_service.download_files(file_ids) as file_paths:
            file_path_strs = [str(x) for x in file_paths]
            with self.io_service.create_temp_pdf_file("Converted") as out_path:
                with out_path.open("wb") as f:
                    f.write(img2pdf.convert(file_path_strs, rotation=Rotation.ifvalid))
                yield out_path

    @staticmethod
    def _get_file_ids(file_data_list: list[FileData]) -> list[str]:
        return [x.id for x in file_data_list]
