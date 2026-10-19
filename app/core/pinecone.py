from pinecone import Pinecone
from app.core.config import settings

# Initialize the Pinecone client using the modern v3+ SDK
pc = Pinecone(api_key=settings.PINECONE_API_KEY)

# Connect to the target serverless or starter index
pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)