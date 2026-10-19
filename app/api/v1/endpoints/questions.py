import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from openai import AsyncOpenAI



router = APIRouter()

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class GenerateImageRequest(BaseModel):
    prompt: str

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-image")
async def upload_question_image(file: UploadFile = File(...)):
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(status_code=400, detail="Only image files are supported.")

    safe_filename = f"q_img_{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Return the static path that the frontend will use to fetch the image
    return {
        "detail": "Image uploaded successfully",
        "image_url": f"/static-uploads/{safe_filename}"
    }



@router.post("/generate-image")
async def generate_question_image(request: GenerateImageRequest):
    try:
        # Generate image using the modern GPT Image API
        response = await openai_client.images.generate(
            model="gpt-image-2.5-flare",
            prompt=request.prompt,
            size="1024x1024",
            response_format="b64_json" # Force raw Base64 output instead of URLs
        )
        
        # Extract and decode the raw Base64 bytes
        image_b64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_b64)
        
        # Save directly to our local uploads directory
        safe_filename = f"ai_diagram_{uuid.uuid4().hex[:8]}.png"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
            
        return {
            "detail": "AI Diagram generated successfully",
            "image_url": f"/static-uploads/{safe_filename}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")