# Telegram PDF Bot

PDF utility bot on Telegram

Connect to [Bot](https://t.me/pdf2bot)

Stay tuned for updates and new releases on the [Telegram Channel](https://t.me/pdf2botdev)

Find the bot at [Store Bot](https://storebot.me/bot/pdf2bot)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and 
testing purposes

### Prerequisites

Run the following command to install the required libraries:

```
pip install -r requirements.txt
```

Below is a list of the main libraries that are included:

* [Python Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot)
* [PyPDF2](https://github.com/mstamy2/PyPDF2)
* [pdf-diff](https://github.com/JoshData/pdf-diff)

You will also need to run the following command to install the requirements for `pdf-diff`:

`apt-get install python3-lxml poppler-utils`

Make a `.env` file and put your telegram token in there. 

If you want to use the webhook method to run the bot, also include `APP_URL` and `PORT` in the `.env` file. If you 
want to use polling instead, do not include `APP_URL` in your `.env` file.

Below is an example:

```
TELEGRAM_TOKEN=<telegram_token>
```