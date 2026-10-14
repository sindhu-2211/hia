import pdfplumber
import streamlit as st
from config.app_config import MAX_PDF_PAGES
from utils.validators import validate_pdf_file, validate_pdf_content


def _ocr_pdf(pdf_file) -> str:
    """OCR fallback using pdf2image + pytesseract."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        from PIL import Image

        pdf_file.seek(0)
        pages = convert_from_bytes(pdf_file.read(), dpi=300)
        text = ""
        for page_img in pages:
            text += pytesseract.image_to_string(page_img) + "\n"
        return text
    except ImportError:
        return ""
    except Exception as e:
        return f"OCR error: {str(e)}"


def extract_text_from_image(image_file) -> str:
    """OCR a JPEG or PNG file directly, with preprocessing for better accuracy."""
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter

        img = Image.open(image_file).convert("RGB")

        # Upscale small images — OCR needs at least 300 DPI equivalent
        min_width = 1200
        if img.width < min_width:
            scale = min_width / img.width
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

        # Grayscale + contrast boost
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_config)

        if not text.strip() or len(text.strip()) < 20:
            return "Could not extract text from image. Image resolution is too low — please upload a clearer, higher-resolution scan (min 300 DPI recommended)."
        return text
    except ImportError:
        return "OCR error: pytesseract or Pillow not installed."
    except Exception as e:
        return f"OCR error: {str(e)}"


def extract_text_from_pdf(pdf_file):
    """Extract and validate text from PDF file. Falls back to OCR for scanned pages."""
    try:
        is_valid, error = validate_pdf_file(pdf_file)
        if not is_valid:
            return error

        text = ""
        needs_ocr = False

        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                return f"PDF exceeds maximum page limit of {MAX_PDF_PAGES}"

            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted and extracted.strip():
                    text += extracted + "\n"
                else:
                    needs_ocr = True
                    break  # one empty page is enough signal

        # If pdfplumber got nothing useful, try OCR
        if needs_ocr or not text.strip():
            st.info("Scanned PDF detected — running OCR, this may take a moment...")
            pdf_file.seek(0)
            ocr_text = _ocr_pdf(pdf_file)

            if ocr_text.startswith("OCR error:"):
                return "Could not extract text from PDF. It appears to be a scanned document and OCR failed: " + ocr_text

            if not ocr_text.strip():
                return "Could not extract text from PDF. Please ensure it's not a scanned document without readable content."

            text = ocr_text

        is_valid, error = validate_pdf_content(text)
        if not is_valid:
            return error

        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"
