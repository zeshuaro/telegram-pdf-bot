from dataclasses import dataclass

import humanize


@dataclass
class CompressResult:
    old_size: int
    new_size: int
    out_path: str

    @property
    def reduced_percentage(self):
        return 1 - self.new_size / self.old_size

    @property
    def readable_old_size(self):
        return self._readable_size(self.old_size)

    @property
    def readable_new_size(self):
        return self._readable_size(self.new_size)

    @staticmethod
    def _readable_size(size: int):
        return humanize.naturalsize(size)


@dataclass
class FontData:
    font_family: str
    font_url: str


@dataclass
class ScaleData:
    x: str
    y: str

    def __str__(self) -> str:
        return f"{self.x} {self.y}"

    @staticmethod
    def from_string(value: str) -> "ScaleData":
        x, y = map(float, value.split())
        return ScaleData(x, y)


class ScaleByData(ScaleData):
    pass


class ScaleToData(ScaleData):
    pass
