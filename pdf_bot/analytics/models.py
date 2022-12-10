from enum import Enum


class TaskType(Enum):
    beautify_image = "beautify_image"
    black_and_white_pdf = "black_and_white_pdf"
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
