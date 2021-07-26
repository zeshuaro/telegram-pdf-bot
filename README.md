# Telegram PDF Bot

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/pdfbot)
[![MIT License](https://img.shields.io/github/license/zeshuaro/telegram-pdf-bot.svg)](https://github.com/zeshuaro/telegram-pdf-bot/blob/master/LICENSE)
[![Deploy](https://github.com/zeshuaro/telegram-pdf-bot/actions/workflows/deploy.yml/badge.svg)](https://github.com/zeshuaro/telegram-pdf-bot/actions/workflows/deploy.yml)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/4044596f649742fdb9b9c0acd80c321e)](https://www.codacy.com/app/zeshuaro/telegram-pdf-bot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=zeshuaro/telegram-pdf-bot&amp;utm_campaign=Badge_Grade)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Crowdin](https://badges.crowdin.net/telegram-pdf-bot/localized.svg)](https://crowdin.com/project/telegram-pdf-bot)
[![Telegram Channel](https://img.shields.io/badge/Telegram-Channel-blue.svg)](https://t.me/pdf2botdev)

A Telegram bot that can:

- Compress, crop, decrypt, encrypt, merge, preview, rename, rotate, scale and split PDF files
- Compare text differences between two PDF files
- Create PDF files from text messages
- Add watermark to PDF files
- Add text layers to PDF files to make them searchable with text
- Extract images and text from PDF files
- Convert PDF files into images
- Beautify handwritten notes images into PDF files
- Convert webpages and images into PDF files

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
python main.py
```
