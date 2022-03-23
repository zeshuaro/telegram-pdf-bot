import os
from enum import Enum
from uuid import UUID

import requests
from dotenv import load_dotenv
from loguru import logger
from requests.exceptions import HTTPError
from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.language import get_lang

load_dotenv()
GA_API_SECRET = os.environ.get("GA_API_SECRET")
GA_MEASUREMENT_ID = os.environ.get("GA_MEASUREMENT_ID")


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
    update: Update, context: CallbackContext, event: TaskType, action: EventAction
) -> None:
    if GA_API_SECRET is not None and GA_MEASUREMENT_ID is not None:
        lang = get_lang(update, context)
        user_id = update.effective_message.from_user.id
        params = {"api_secret": GA_API_SECRET, "measurement_id": GA_MEASUREMENT_ID}
        json = {
            "client_id": str(UUID(int=user_id)),
            "user_id": str(user_id),
            "user_properties": {"bot_language": {"value": lang}},
            "events": [
                {
                    "name": event.value,
                    "params": {"action": action.value},
                }
            ],
        }

        try:
            r = requests.post(
                "https://www.google-analytics.com/mp/collect",
                params=params,
                json=json,
            )
            r.raise_for_status()
        except HTTPError:
            logger.exception("Failed to send analytics")
