import logging
from google.cloud import storage
from config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self._initialize_storage()

    def _normalize_bucket_name(self, name: str) -> str:
        name = (name or "").strip()
        if name.startswith("gs://"):
            name = name[5:]
        # NO convertir dominios de Firebase a appspot: usamos el nombre tal cual
        if "://" in name:
            name = name.split("://", 1)[1].split("/", 1)[0]
        return name

    def _initialize_storage(self):
        self.client = storage.Client(project=settings.PROJECT_ID)
        bucket_name = self._normalize_bucket_name(settings.STORAGE_BUCKET)
        self.bucket = self.client.bucket(bucket_name)
        logger.info("Cloud Storage initialized - bucket: %s", bucket_name)
        print("DEBUG Storage bucket ->", bucket_name)  # ayuda visual

    def upload_bytes(self, data: bytes, dest_path: str, content_type: str = "application/octet-stream") -> str:
        blob = self.bucket.blob(dest_path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket.name}/{dest_path}"
