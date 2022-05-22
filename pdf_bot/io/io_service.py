from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Generator


class IOService:
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
