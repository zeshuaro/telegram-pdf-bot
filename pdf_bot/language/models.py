from pydantic import BaseModel


class SetLanguageData:
    pass


class LanguageData(BaseModel):
    label: str
    long_code: str

    @property
    def short_code(self) -> str:
        return self.long_code.split("_")[0]
