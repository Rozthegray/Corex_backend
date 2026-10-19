from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, documents, payments

api_router = APIRouter()

# Week 1 Routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["RAG Interface"])
api_router.include_router(documents.router, prefix="/documents", tags=["Knowledge Base"])

# Week 2 Routes
api_router.include_router(payments.router, prefix="/payments", tags=["Billing & Subscriptions"])

from app.api.v1.endpoints import admin, legal
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
api_router.include_router(legal.router, prefix="/legal", tags=["Legal & Privacy"])

from app.api.v1.endpoints import user_state, mock_exam, summarizer

api_router.include_router(user_state.router, prefix="/user", tags=["User State & Profile"])
api_router.include_router(mock_exam.router, prefix="/mock-exams", tags=["AI Mock Exam Engine"])
api_router.include_router(summarizer.router, prefix="/summarizer", tags=["Topic Summarizer"])