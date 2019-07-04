from pdf_bot.commands import compare_cov_handler, merge_cov_handler, watermark_cov_handler
from pdf_bot.files import file_cov_handler
from pdf_bot.photos import photo_cov_handler
from pdf_bot.url import url_to_pdf
from pdf_bot.payment import send_payment_options, send_payment_invoice, successful_payment, precheckout_check, \
    payment_cov_handler
from pdf_bot.feedback import feedback_cov_handler
from pdf_bot.constants import *
from pdf_bot.stats import update_stats
