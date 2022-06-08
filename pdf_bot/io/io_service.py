from contextlib import contextmanager
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Generator, List


class IOService:
    @staticmethod
    @contextmanager
    def create_temp_directory() -> Generator[str, None, None]:
        try:
            td = TemporaryDirectory()
            yield td.name
        finally:
            td.cleanup()

    @staticmethod
    @contextmanager
    def create_temp_file(
        prefix: str | None = None, suffix: str | None = None
    ) -> Generator[str, None, None]:
        if prefix is not None and not prefix.endswith("_"):
            prefix += "_"

        try:
            tf = NamedTemporaryFile(prefix=prefix, suffix=suffix)
            yield tf.name
        finally:
            tf.close()

    @staticmethod
    @contextmanager
    def create_temp_files(num_files: int) -> Generator[List[str], None, None]:
        try:
            tempfiles = [NamedTemporaryFile() for _ in range(num_files)]
            yield [x.name for x in tempfiles]
        finally:
            for tf in tempfiles:
                tf.close()

    @contextmanager
    def create_temp_pdf_file(self, prefix: str) -> Generator[str, None, None]:
        try:
            with self.create_temp_file(prefix=prefix, suffix=".pdf") as out_path:
                yield out_path
        finally:
            pass

    @contextmanager
    def create_temp_png_file(self, prefix: str) -> Generator[str, None, None]:
        try:
            with self.create_temp_file(prefix=prefix, suffix=".png") as out_path:
                yield out_path
        finally:
            pass

    @contextmanager
    def create_temp_txt_file(self, prefix: str) -> Generator[str, None, None]:
        try:
            with self.create_temp_file(prefix=prefix, suffix=".txt") as out_path:
                yield out_path
        finally:
            pass
