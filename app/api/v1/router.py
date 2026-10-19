from fastapi import APIRouter
from app.api.v1.endpoints import documents
from app.api.v1.endpoints import documents, chat
from app.api.v1.endpoints import documents, chat, questions, auth # Add questions here

# ... existing routes ...

# Initialize the central router
api_router = APIRouter()

# Register the documents route
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

api_router.include_router(questions.router, prefix="/questions", tags=["questions"])

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

api_router.include_router(admin.router, prefix="/admin", tags=["admin"]) # <-- Register the route
