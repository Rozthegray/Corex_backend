import io
import tiktoken
from typing import List
from pypdf import PdfReader

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text from a PDF file in memory."""
    reader = PdfReader(io.BytesIO(file_bytes))
    extracted_text = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text.append(text)
            
    return "\n".join(extracted_text)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits text into chunks of `chunk_size` tokens, overlapping by `overlap` tokens.
    Uses 'cl100k_base' which matches OpenAI embeddings and Claude standard tokenization.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    chunks = []
    start = 0
    total_tokens = len(tokens)
    
    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_tokens = tokens[start:end]
        chunks.append(encoding.decode(chunk_tokens))
        
        if end == total_tokens:
            break
            
        start += (chunk_size - overlap)
        
    return chunks