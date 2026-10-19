from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "School Academic Archive API"
    API_V1_STR: str = "/api/v1"
    
    # Database
    SQLALCHEMY_DATABASE_URI: str
    
    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str  # Added to prevent the AttributeError


    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1440 minutes = 24 hours

    OPENAI_API_KEY: str
    
    # Redis
    REDIS_URL: str

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()