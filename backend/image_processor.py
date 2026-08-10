"""
Extracts text from an image (e.g. a screenshot of slides or notes) via
Tesseract OCR. Requires the `tesseract` binary to be installed and on
PATH (on Ubuntu/Debian: `apt-get install tesseract-ocr`).
"""

from PIL import Image
import pytesseract


def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()
