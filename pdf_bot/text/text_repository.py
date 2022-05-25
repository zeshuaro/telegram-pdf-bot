import os

from dotenv import load_dotenv
from requests import Session

from pdf_bot.text.models import FontData

load_dotenv()
GOOGLE_FONTS_TOKEN = os.environ.get("GOOGLE_FONTS_TOKEN")


class TextRepository:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or Session()
        self.session.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }

    def get_font(self, font: str) -> FontData | None:
        font_data: FontData | None = None
        font = font.lower()

        r = self.session.get(
            f"https://www.googleapis.com/webfonts/v1/webfonts?key={GOOGLE_FONTS_TOKEN}"
        )

        for item in r.json()["items"]:
            if item["family"].lower() == font:
                if "regular" in item["files"]:
                    font_data = FontData(item["family"], item["files"]["regular"])
                break

        return font_data
