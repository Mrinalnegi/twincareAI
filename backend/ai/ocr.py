"""OCR pipeline: PDF/image → raw text extraction.

Uses pytesseract as the primary OCR engine (reliable, easy Docker install).
Falls back to LLM-based extraction via Fireworks API for better accuracy.
"""

import os
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def pdf_to_images(pdf_path: str) -> list[Image.Image]:
    """Convert a PDF file to a list of PIL Images."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=300)
        logger.info(f"Converted PDF to {len(images)} page(s)")
        return images
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        raise ValueError(f"Failed to convert PDF: {e}")


def image_to_text_tesseract(image: Image.Image) -> str:
    """Extract text from an image using Tesseract OCR."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        return ""


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from a PDF or image file.
    
    Returns the concatenated raw text from all pages.
    """
    ext = Path(file_path).suffix.lower()
    
    if ext == ".pdf":
        # 1. Try extracting text directly using pypdf (extremely fast, no poppler/tesseract dependencies)
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            extracted_texts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 10:
                    extracted_texts.append(f"--- Page {i + 1} ---\n{page_text}")
            
            if extracted_texts:
                full_text = "\n\n".join(extracted_texts)
                logger.info(f"Directly extracted {len(full_text)} characters using pypdf")
                return full_text
        except Exception as pe:
            logger.warning(f"Direct PDF text extraction failed: {pe}. Falling back to OCR.")

        # 2. Fall back to Poppler + Tesseract OCR if direct text extraction is empty
        images = pdf_to_images(file_path)
        texts = []
        for i, img in enumerate(images):
            logger.info(f"Processing page {i + 1}/{len(images)}")
            text = image_to_text_tesseract(img)
            if text:
                texts.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(texts)
    
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        img = Image.open(file_path)
        return image_to_text_tesseract(img)
    
    else:
        raise ValueError(f"Unsupported file type: {ext}")



def is_ocr_available() -> bool:
    """Check if Tesseract OCR is available."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
