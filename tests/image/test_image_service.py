from unittest.mock import MagicMock, patch

import pytest
from img2pdf import Rotation

from pdf_bot.cli import CLIService
from pdf_bot.image import ImageService
from pdf_bot.io_internal.io_service import IOService
from pdf_bot.models import FileData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestImageService(LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin):
    PASSWORD = "password"
    FILE_PATH_STEM = "file_path_stem"

    def setup_method(self) -> None:
        super().setup_method()
        self.cli_service = MagicMock(spec=CLIService)
        self.telegram_service = self.mock_telegram_service()

        self.io_service = MagicMock(spec=IOService)
        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = self.file_path

        self.sut = ImageService(
            self.cli_service,
            self.io_service,
            self.telegram_service,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_files", [0, 1, 2, 5])
    async def test_beautify_and_convert_images_to_pdf(self, num_files: int) -> None:
        self.file_path.stem = self.FILE_PATH_STEM
        file_data_list, file_ids, file_paths = self._get_file_data_list(num_files)
        self.telegram_service.download_files.return_value.__aenter__.return_value = file_paths

        with patch("pdf_bot.image.image_service.noteshrink") as noteshrink:
            async with self.sut.beautify_and_convert_images_to_pdf(file_data_list) as actual:
                assert actual == self.file_path
                self.telegram_service.download_files.assert_called_once_with(file_ids)
                self.io_service.create_temp_pdf_file.assert_called_once_with("Beautified")
                noteshrink.notescan_main.assert_called_once_with(
                    file_paths,
                    basename=f"{self.FILE_PATH_STEM}_page",
                    pdfname=self.file_path,
                )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_files", [0, 1, 2, 5])
    async def test_convert_images_to_pdf(self, num_files: int) -> None:
        image_bytes = "image_bytes"
        file_data_list, file_ids, file_paths = self._get_file_data_list(num_files)
        buffered_writer = self.mock_path_open(self.file_path)

        file_path_strs = [str(x) for x in file_paths]
        self.telegram_service.download_files.return_value.__aenter__.return_value = file_paths

        with patch("pdf_bot.image.image_service.img2pdf") as img2pdf:
            img2pdf.convert.return_value = image_bytes

            async with self.sut.convert_images_to_pdf(file_data_list) as actual:
                assert actual == self.file_path

                self.telegram_service.download_files.assert_called_once_with(file_ids)
                self.io_service.create_temp_pdf_file.assert_called_once_with("Converted")

                self.file_path.open.assert_called_once_with("wb")
                img2pdf.convert.assert_called_once_with(file_path_strs, rotation=Rotation.ifvalid)
                buffered_writer.write.assert_called_once_with(image_bytes)

    def _get_file_data_list(
        self, num_files: int
    ) -> tuple[list[FileData], list[str], list[MagicMock]]:
        file_data_list = []
        file_ids = []
        file_paths = []

        for i in range(num_files):
            file_data = FileData(f"id_{i}", f"name_{i}")
            file_data_list.append(file_data)
            file_ids.append(file_data.id)
            file_paths.append(self.mock_file_path())

        return file_data_list, file_ids, file_paths
