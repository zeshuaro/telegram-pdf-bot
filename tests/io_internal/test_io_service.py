from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from pdf_bot.io_internal import IOService


class TestIOService:
    FILE_NAME = "file_name"
    FILE_PATH = Path(FILE_NAME)
    FILE_PREFIX = "file_prefix"
    FILE_PREFIX_UNDERSCORE = f"{FILE_PREFIX}_"
    FILE_SUFFIX = "file_suffix"

    def setup_method(self) -> None:
        self.tf = MagicMock()
        self.tf.name = self.FILE_NAME

        self.tf_cls_patcher = patch(
            "pdf_bot.io_internal.io_service.NamedTemporaryFile", return_value=self.tf
        )
        self.tf_cls = self.tf_cls_patcher.start()

        self.sut = IOService()

    def teardown_method(self) -> None:
        self.tf_cls_patcher.stop()

    @pytest.mark.parametrize("prefix", [None, FILE_PREFIX, FILE_PREFIX_UNDERSCORE])
    @pytest.mark.asyncio
    async def test_create_temp_directory(self, prefix: str | None) -> None:
        dir_name = "dir_name"
        td = MagicMock(spec=TemporaryDirectory)

        with patch("pdf_bot.io_internal.io_service.TemporaryDirectory") as td_cls:
            td_cls.return_value = td
            td.name = dir_name

            with self.sut.create_temp_directory(prefix) as actual:
                assert actual == Path(dir_name)

            expected_prefix = self._get_expected_prefix(prefix)
            td_cls.assert_called_once_with(prefix=expected_prefix)
            td.cleanup.assert_called_once()

    @pytest.mark.parametrize(
        ("prefix", "suffix"),
        [
            (None, None),
            (FILE_PREFIX, None),
            (FILE_PREFIX_UNDERSCORE, None),
            (None, FILE_SUFFIX),
            (FILE_PREFIX, FILE_SUFFIX),
            (FILE_PREFIX_UNDERSCORE, FILE_SUFFIX),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_temp_file(self, prefix: str | None, suffix: str | None) -> None:
        with self.sut.create_temp_file(prefix, suffix) as actual:
            assert actual == self.FILE_PATH

        expected_prefix = self._get_expected_prefix(prefix)
        self._assert_temp_file(expected_prefix, suffix)

    @pytest.mark.parametrize("num_files", [0, 1, 2, 5])
    @pytest.mark.asyncio
    async def test_create_temp_files(self, num_files: int) -> None:
        files = []
        paths = []

        for i in range(num_files):
            name = f"{self.FILE_NAME}_{i}"
            file = MagicMock()
            file.name = name

            files.append(file)
            paths.append(Path(name))

        index = 0

        def create_tmp_file() -> MagicMock:
            nonlocal index
            file = files[index]
            index += 1
            return file

        with patch("pdf_bot.io_internal.io_service.NamedTemporaryFile") as tf:
            tf.side_effect = create_tmp_file
            with self.sut.create_temp_files(num_files) as actual:
                assert actual == paths

            for file in files:
                file.close.assert_called_once()

    @pytest.mark.parametrize("prefix", [None, FILE_PREFIX, FILE_PREFIX_UNDERSCORE])
    @pytest.mark.asyncio
    async def test_create_temp_pdf_file(self, prefix: str | None) -> None:
        with self.sut.create_temp_pdf_file(prefix) as actual:
            assert actual == self.FILE_PATH

        expected_prefix = self._get_expected_prefix(prefix)
        self._assert_temp_file(expected_prefix, ".pdf")

    @pytest.mark.asyncio
    async def test_create_temp_png_file(self) -> None:
        with self.sut.create_temp_png_file(self.FILE_PREFIX_UNDERSCORE) as actual:
            assert actual == self.FILE_PATH
        self._assert_temp_file(self.FILE_PREFIX_UNDERSCORE, ".png")

    @pytest.mark.asyncio
    async def test_create_temp_txt_file(self) -> None:
        with self.sut.create_temp_txt_file(self.FILE_PREFIX_UNDERSCORE) as actual:
            assert actual == self.FILE_PATH
        self._assert_temp_file(self.FILE_PREFIX_UNDERSCORE, ".txt")

    def _assert_temp_file(self, prefix: str | None, suffix: str | None) -> None:
        self.tf_cls.assert_called_once_with(prefix=prefix, suffix=suffix)
        self.tf.close.assert_called_once()

    def _get_expected_prefix(self, prefix: str | None) -> str | None:
        if prefix is not None and not prefix.endswith("_"):
            return f"{prefix}_"
        return prefix
