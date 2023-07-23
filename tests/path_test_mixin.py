from io import BufferedWriter
from os import stat_result
from pathlib import Path
from unittest.mock import MagicMock


class PathTestMixin:
    @staticmethod
    def mock_file_path() -> MagicMock:
        path = MagicMock(spec=Path)
        path.is_dir.return_value = False
        return path

    @staticmethod
    def mock_dir_path() -> MagicMock:
        path = MagicMock(spec=Path)
        path.is_dir.return_value = True
        return path

    @staticmethod
    def mock_path_open(path: MagicMock) -> MagicMock:
        writer = MagicMock(spec=BufferedWriter)
        path.open.return_value.__enter__.return_value = writer
        return writer

    @staticmethod
    def mock_path_stat(path: MagicMock) -> MagicMock:
        stat = MagicMock(spec=stat_result)
        path.stat.return_value = stat
        return stat
