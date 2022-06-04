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
