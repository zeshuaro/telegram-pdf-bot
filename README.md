# Telegram PDF Bot

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/pdfbot)
[![Telegram Channel](https://img.shields.io/badge/Telegram-Channel-blue.svg)](https://t.me/pdf2botdev)
[![MIT License](https://img.shields.io/github/license/zeshuaro/telegram-pdf-bot.svg)](https://github.com/zeshuaro/telegram-pdf-bot/blob/master/LICENSE)

[![Build Status](https://travis-ci.com/zeshuaro/telegram-pdf-bot.svg?branch=master)](https://travis-ci.com/zeshuaro/telegram-pdf-bot)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/4044596f649742fdb9b9c0acd80c321e)](https://www.codacy.com/app/zeshuaro/telegram-pdf-bot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=zeshuaro/telegram-pdf-bot&amp;utm_campaign=Badge_Grade)
[![Crowdin](https://badges.crowdin.net/telegram-pdf-bot/localized.svg)](https://crowdin.com/project/telegram-pdf-bot)

A PDF utility bot on Telegram that can:

- Compare, crop, decrypt, encrypt, merge, rotate, scale, split and add a watermark to a PDF file
- Extract images in a PDF file and convert a PDF file into images
- Beautify and convert photos into PDF format
- Convert a web page into a PDF file

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes

### Setup Database

The bot uses [Datastore](https://cloud.google.com/datastore) on Google Cloud Platform (GCP). Create a new project on GCP and enabble Datastore in the project. Install the [gcloud CLI](https://cloud.google.com/sdk/) and run `gcloud init` to initialise it with your project.

### OS Requirements

Ubuntu

```sh
apt-get install poppler-utils libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

macOS
```sh
brew install libxml2 libxslt poppler cairo pango gdk-pixbuf libffi
```

### Setup Virtual Environment

Create a virtual environment with the following command:

```sh
virtualenv venv
source venv/bin/activate
```

### Bot Requirements

Run the following command to install the required packages:

```sh
pip install -r requirements.txt
```

### Compile the translation files

Run the following command to compile all the translation files:

```sh
pybabel compile -D pdf_bot -d locale/
```

### Setup Your Environment Variables

Copy the `.env` example file and edit the variables within the file:

```sh
cp .env.example .env
```

### Running The Bot

You can then start the bot with the following command:

```bash
python bot.py
```
