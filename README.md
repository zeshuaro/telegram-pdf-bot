# Telegram PDF Bot

PDF utility bot on Telegram

Connect to [Bot](https://t.me/pdf2bot)

Stay tuned for updates and new releases on the [Telegram Channel](https://t.me/pdf2botdev)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and 
testing purposes

### Prerequisites

```
pip install -r requirements.txt
```

Make a `.env` file and put your telegram token in there. 

If you want to use the webhook method to run the bot, also include `APP_URL` and `PORT` in the `.env` file. If you 
want to use polling instead, do not include `APP_URL` in your `.env` file.

Below is an example:

```
TELEGRAM_TOKEN=<telegram_token>
```