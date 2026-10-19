import io
import pymupdf as fitz
import pytesseract
from PIL import Image

# Configure Tesseract path for your Windows environment
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_multimodal_content(file_bytes: bytes, filename: str) -> str:
    """Extracts text from PDFs, OCRs embedded images, or OCRs standalone images."""
    extracted_content = []
    
    # 1. Handle Standalone Images (PNG, JPG, JPEG)
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img = Image.open(io.BytesIO(file_bytes))
        ocr_text = pytesseract.image_to_string(img)
        return f"[Image Content]: {ocr_text}"

    # 2. Handle PDFs with embedded images
    if filename.lower().endswith('.pdf'):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num, page in enumerate(doc):
            # Get raw text
            text = page.get_text()
            if text.strip():
                extracted_content.append(text)
                
            # Scan for embedded images on the page
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # OCR the embedded diagram/image
                img = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text.strip():
                    extracted_content.append(f"\n[Diagram OCR (Page {page_num + 1})]:\n{ocr_text}\n")
                    
        return "\n".join(extracted_content)

    return ""