# Telegram PDF Bot

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/pdf2bot)
[![Telegram Channel](https://img.shields.io/badge/Telegram-Channel-blue.svg)](https://t.me/pdf2botdev)
[![MIT License](https://img.shields.io/badge/license-MIT%20License-lightgrey.svg)](https://github.com/zeshuaro/telegram-pdf-bot/blob/master/LICENSE)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/4044596f649742fdb9b9c0acd80c321e)](https://www.codacy.com/app/zeshuaro/telegram-pdf-bot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=zeshuaro/telegram-pdf-bot&amp;utm_campaign=Badge_Grade)

A PDF utility bot on Telegram that can:

- Compare, crop, decrypt, encrypt, merge, rotate, scale, split and add a watermark to a PDF file
- Extract images in a PDF file and convert a PDF file into images
- Beautify and convert photos into PDF format
- Convert a web page into a PDF file

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and 
testing purposes

### Prerequisites

#### OS Requirements

Ubuntu

```bash
apt-get install poppler-utils libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

macOS
```bash
brew install libxml2 libxslt poppler cairo pango gdk-pixbuf libffi
```

#### Bot Requirements
Run the following command to install the required packages:

```bash
pip install -r requirements.txt
```

### Setup Your Environment Variables

Make a `.env` file and put your telegram token in there. Below is an example:

```dotenv
TELE_TOKEN=<telegram_token>
```

### Running The Bot

You can then start the bot with the following command:

```bash
python bot.py
```