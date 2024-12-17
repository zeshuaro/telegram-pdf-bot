from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory


class IOService:
    @staticmethod
    @contextmanager
    def create_temp_directory(prefix: str | None = None) -> Generator[Path, None, None]:
        if prefix is not None and not prefix.endswith("_"):
            prefix += "_"

        try:
            td = TemporaryDirectory(prefix=prefix)
            yield Path(td.name)
        finally:
            td.cleanup()

    @staticmethod
    @contextmanager
    def create_temp_file(
        prefix: str | None = None, suffix: str | None = None
    ) -> Generator[Path, None, None]:
        if prefix is not None and not prefix.endswith("_"):
            prefix += "_"

        try:
            tf = NamedTemporaryFile(prefix=prefix, suffix=suffix)  # noqa: SIM115
            yield Path(tf.name)
        finally:
            tf.close()

    @staticmethod
    @contextmanager
    def create_temp_files(num_files: int) -> Generator[list[Path], None, None]:
        try:
            tempfiles = [NamedTemporaryFile() for _ in range(num_files)]  # noqa: SIM115
            yield [Path(x.name) for x in tempfiles]
        finally:
            for tf in tempfiles:
                tf.close()

    @contextmanager
    def create_temp_pdf_file(self, prefix: str | None = None) -> Generator[Path, None, None]:
        with self.create_temp_file(prefix=prefix, suffix=".pdf") as path:
            yield path

    @contextmanager
    def create_temp_png_file(self, prefix: str) -> Generator[Path, None, None]:
        with self.create_temp_file(prefix=prefix, suffix=".png") as out_path:
            yield out_path

    @contextmanager
    def create_temp_txt_file(self, prefix: str) -> Generator[Path, None, None]:
        with self.create_temp_file(prefix=prefix, suffix=".txt") as out_path:
            yield out_path
