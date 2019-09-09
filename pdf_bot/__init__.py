from pdf_bot.commands import compare_cov_handler, merge_cov_handler, watermark_cov_handler, \
    photo_cov_handler
from pdf_bot.files import file_cov_handler
from pdf_bot.url import url_to_pdf
from pdf_bot.payment import send_support_options_without_async, send_support_options_with_async, \
    send_payment_invoice, successful_payment, precheckout_check, receive_custom_amount
from pdf_bot.feedback import feedback_cov_handler
from pdf_bot.constants import *
from pdf_bot.language import set_lang, send_lang, store_lang
from pdf_bot.store import create_user
from pdf_bot.stats import get_stats
