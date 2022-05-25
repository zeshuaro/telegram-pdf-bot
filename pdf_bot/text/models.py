class FontData:
    def __init__(self, font_family: str, font_url: str) -> None:
        self.font_family = font_family
        self.font_url = font_url

    def __eq__(self, o: "FontData") -> bool:
        return self.font_family == o.font_family and self.font_url == o.font_url
