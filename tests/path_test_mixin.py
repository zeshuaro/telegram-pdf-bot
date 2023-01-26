from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch


class PathTestMixin:
    def mock_file_path(self) -> MagicMock:
        return MagicMock(spec=Path)

    @contextmanager
    def mock_dir_path(self) -> Generator[MagicMock, None, None]:
        path = self.mock_file_path()
        with patch.object(Path, "is_dir") as is_dir:
            is_dir.return_value = True
            yield path
