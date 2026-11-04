import io
import os
import gc
import pymupdf as fitz
import pytesseract
from PIL import Image

def extract_multimodal_content(file_bytes: bytes, filename: str) -> str:
    """Memory-optimized extraction for free-tier deployments."""
    extracted_content = []
    
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img = Image.open(io.BytesIO(file_bytes))
        ocr_text = pytesseract.image_to_string(img)
        img.close()
        return f"[Image Content]: {ocr_text}"

    if filename.lower().endswith('.pdf'):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # 1. Extract raw text
            text = page.get_text()
            if text.strip():
                extracted_content.append(text)
                
            # 2. Extract embedded images with strict memory cleanup
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Open, OCR, and immediately close/delete
                img = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(img)
                img.close()
                del image_bytes
                
                if ocr_text.strip():
                    extracted_content.append(f"\n[Diagram OCR (Page {page_num + 1})]:\n{ocr_text}\n")
            
            # Force garbage collection after every page
            gc.collect()
            
        doc.close()
        return "\n".join(extracted_content)

    return ""
