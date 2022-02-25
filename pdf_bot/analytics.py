import os
from enum import Enum
from uuid import UUID

import requests
from dotenv import load_dotenv
from logbook import Logger
from requests.exceptions import HTTPError
from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.language import get_lang

load_dotenv()
TRACKING_ID = os.environ.get("GA_TRACKING_ID")


class TaskType(Enum):
    beautify_image = "beautify_image"
    compare_pdf = "compare_pdf"
    compress_pdf = "compress_pdf"
    crop_pdf = "crop_pdf"
    decrypt_pdf = "decrypt_pdf"
    encrypt_pdf = "encrypt_pdf"
    get_pdf_image = "get_pdf_image"
    get_pdf_text = "get_pdf_text"
    image_to_pdf = "image_to_pdf"
    merge_pdf = "merge_pdf"
    ocr_pdf = "ocr_pdf"
    pdf_to_image = "pdf_to_image"
    preview_pdf = "preview_pdf"
    rename_pdf = "rename_pdf"
    rotate_pdf = "rotate_pdf"
    scale_pdf = "scale_pdf"
    split_pdf = "split_pdf"
    text_to_pdf = "text_to_pdf"
    url_to_pdf = "url_to_pdf"
    watermark_pdf = "watermark_pdf"


class EventAction(Enum):
    complete = "complete"


def send_event(
    update: Update, context: CallbackContext, category: TaskType, action: EventAction
) -> None:
    logger = Logger()
    if TRACKING_ID is not None:
        lang = get_lang(update, context)
        payload = {
            "v": 1,
            "tid": TRACKING_ID,
            "ua": "Apache/2.4.34 (Ubuntu) OpenSSL/1.1.1 (internal dummy connection)",
            "ds": "telegram",
            "cid": UUID(int=update.effective_message.from_user.id),
            "ul": lang,
            "t": "event",
            "ec": category.value,
            "ea": action.value,
        }
        data = "&".join(f"{key}={value}" for key, value in payload.items())

        try:
            r = requests.post("https://www.google-analytics.com/collect", data=data)
            r.raise_for_status()
        except HTTPError:
            logger.exception("Failed to send analytics")
