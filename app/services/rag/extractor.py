import io
import pymupdf as fitz

def extract_multimodal_content(file_bytes: bytes, filename: str) -> str:
    """
    Low-RAM extraction for free-tier deployments. 
    Extracts native text from PDFs but skips heavy image OCR to prevent OOM crashes.
    """
    extracted_content = []
    
    # 1. Handle Standalone Images (Graceful fallback)
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        return "[Image Content]: Image OCR is disabled in low-memory environments. Please upload a PDF document."

    # 2. Handle PDFs (Text Extraction Only)
    if filename.lower().endswith('.pdf'):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract native text (highly memory efficient)
                text = page.get_text()
                if text.strip():
                    extracted_content.append(text)
                    
            doc.close()
            return "\n\n".join(extracted_content)
        except Exception as e:
            print(f"PDF Parsing Error: {str(e)}")
            return ""

    return ""
