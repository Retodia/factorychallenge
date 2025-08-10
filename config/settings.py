import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Google Cloud Project Settings
    PROJECT_ID: str = "challengefactory-68021"
    REGION: str = "us-central1"
    
    # Firebase/Firestore Settings
    FIRESTORE_DB: str = "(default)"
    
    # Collection names
    COLLECTION_USERS: str = "users"
    COLLECTION_INFOUSER: str = "infouser" 
    COLLECTION_AVANCES: str = "avances"
    COLLECTION_RETOS: str = "retosdiarios"
    
    # Cloud Storage Settings
    STORAGE_BUCKET: str = "challengefactory-68021.firebasestorage.app"
    IMAGES_FOLDER: str = "imagenes"
    PODCASTS_FOLDER: str = "podcasts"
    
    # Vertex AI Settings
    VERTEX_AI_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-1.5-pro"
    IMAGEN_MODEL: str = "imagegeneration@006"
    
    # Cloud Text-to-Speech Settings
    TTS_VOICE_FEMALE: str = "es-MX-Neural2-A"
    TTS_VOICE_MALE: str = "es-MX-Neural2-B"
    TTS_LANGUAGE: str = "es-MX"
    
    # Service Account (for local development)
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", 
        "/app/credentials/serviceAccountKey.json"
    )
    
    # Prompt files paths
    PROMPTS_DIR: str = "/app/prompts"
    PROMPT1_FILE: str = "prompt1.txt"
    PROMPT_RETODIA_FILE: str = "prompt_retodia.txt"
    PROMPT_IMAGEN_FILE: str = "prompt_imagen.txt"
    PROMPT_PODCAST_FILE: str = "prompt_podcast.txt"
    
    # Application Settings
    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENT_USERS: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Helper functions
def get_prompt_file_path(filename: str) -> str:
    """Get full path to prompt file"""
    return os.path.join(settings.PROMPTS_DIR, filename)

def get_storage_path(folder: str, user_id: str, filename: str) -> str:
    """Generate Cloud Storage path"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{folder}/{user_id}/{today}/{filename}"