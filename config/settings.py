from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    STORAGE_BUCKET: str
    # Alias para tomar el valor desde GOOGLE_CLOUD_PROJECT del .env
    PROJECT_ID: str = Field(..., validation_alias="GOOGLE_CLOUD_PROJECT")
    # Región por defecto para Vertex AI (ajústala si usas otra)
    VERTEX_AI_LOCATION: str = Field(default="us-central1", validation_alias="VERTEX_AI_LOCATION")

    # Credenciales GCP (ruta al JSON)
    GOOGLE_APPLICATION_CREDENTIALS: str | None = Field(default=None, validation_alias="GOOGLE_APPLICATION_CREDENTIALS")

    # API key de Gemini (google-genai) para TTS u otros
    GOOGLE_API_KEY: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")

    # Opcional: bucket (si lo usas en StorageService)
    FIREBASE_STORAGE_BUCKET: str | None = Field(default=None, validation_alias="FIREBASE_STORAGE_BUCKET")
    GCS_BUCKET: str | None = Field(default=None, validation_alias="GCS_BUCKET")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # <— Ignora claves extra (evita el ValidationError)
        case_sensitive=False,
    )

settings = Settings()
