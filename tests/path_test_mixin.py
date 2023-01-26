from pathlib import Path
from unittest.mock import MagicMock


class PathTestMixin:
    def mock_file_path(self) -> MagicMock:
        path = MagicMock(spec=Path)
        path.is_dir.return_value = False
        return path

    def mock_dir_path(self) -> MagicMock:
        path = MagicMock(spec=Path)
        path.is_dir.return_value = True
        return path
