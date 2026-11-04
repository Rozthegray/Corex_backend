import io
import base64
import pymupdf as fitz
from PIL import Image
from openai import OpenAI
from app.core.config import settings

# Initialize synchronous OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def _ocr_with_openai(image_bytes: bytes) -> str:
    """Offloads OCR to GPT-4o-mini to save RAM on Render Free Tier."""
    try:
        # Compress image to save network bandwidth and API tokens
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Downscale if the image is massive
        img.thumbnail((1024, 1024))
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        img.close()
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Extract all the text from this academic image exactly as written. If there are diagrams, summarize them briefly. If there is absolutely no text or useful information, return exactly the word 'EMPTY_IMAGE'."
                        },
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            max_tokens=700
        )
        
        result = response.choices[0].message.content.strip()
        return "" if result == "EMPTY_IMAGE" else result
    except Exception as e:
        print(f"OpenAI OCR Error: {e}")
        return ""


def extract_multimodal_content(file_bytes: bytes, filename: str) -> str:
    """Extracts text from PDFs and offloads image OCR to OpenAI."""
    extracted_content = []
    
    # 1. Handle Standalone Images
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        ocr_text = _ocr_with_openai(file_bytes)
        return f"[Image Content]: {ocr_text}"

    # 2. Handle PDFs
    if filename.lower().endswith('.pdf'):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract native text (highly memory efficient)
            text = page.get_text()
            if text.strip():
                extracted_content.append(text)
                
            # Scan for embedded images on the page
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # OCR the embedded diagram via OpenAI
                ocr_text = _ocr_with_openai(image_bytes)
                
                if ocr_text.strip():
                    extracted_content.append(f"\n[Diagram OCR (Page {page_num + 1})]:\n{ocr_text}\n")
                    
        doc.close()
        return "\n\n".join(extracted_content)

    return ""
