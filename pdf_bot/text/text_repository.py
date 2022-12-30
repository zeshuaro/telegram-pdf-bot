from requests import Session

from pdf_bot.pdf import FontData


class TextRepository:
    def __init__(self, api_client: Session, google_fonts_token: str) -> None:
        self.api_client = api_client
        self.google_fonts_token = google_fonts_token

    def get_font(self, font: str) -> FontData | None:
        font_data: FontData | None = None
        font = font.lower()

        r = self.api_client.get(
            "https://www.googleapis.com/webfonts/v1/webfonts",
            params={"key": self.google_fonts_token},
        )

        for item in r.json()["items"]:
            if item["family"].lower() == font:
                if "regular" in item["files"]:
                    font_data = FontData(item["family"], item["files"]["regular"])
                break

        return font_data
