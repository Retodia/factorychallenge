import logging
from typing import Optional
from google.cloud import storage
from datetime import datetime
from config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    """Service for Google Cloud Storage operations"""
    
    def __init__(self):
        self.client = None
        self.bucket = None
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize Cloud Storage client"""
        try:
            self.client = storage.Client(project=settings.PROJECT_ID)
            
            # Get bucket (remove gs:// prefix if present)
            bucket_name = settings.STORAGE_BUCKET.replace("gs://", "")
            self.bucket = self.client.bucket(bucket_name)
            
            logger.info(f"Cloud Storage initialized successfully - bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Error initializing Cloud Storage: {str(e)}")
            raise
    
    async def upload_image(self, image_bytes: bytes, user_id: str) -> Optional[str]:
        """
        Upload generated image to Cloud Storage
        Returns: Public URL or None if error
        """
        try:
            # Generate file path
            today = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"challenge_{timestamp}.png"
            blob_path = f"{settings.IMAGES_FOLDER}/{user_id}/{today}/{filename}"
            
            # Upload to Cloud Storage
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                image_bytes,
                content_type='image/png'
            )
            
            # Make blob public (or use signed URLs for security)
            blob.make_public()
            
            # Get public URL
            public_url = blob.public_url
            
            logger.info(f"Image uploaded successfully for user {user_id}: {blob_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading image for user {user_id}: {str(e)}")
            return None
    
    async def upload_podcast(self, audio_bytes: bytes, user_id: str) -> Optional[str]:
        """
        Upload generated podcast to Cloud Storage
        Returns: Public URL or None if error
        """
        try:
            # Generate file path
            today = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"podcast_{timestamp}.mp3"
            blob_path = f"{settings.PODCASTS_FOLDER}/{user_id}/{today}/{filename}"
            
            # Upload to Cloud Storage
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                audio_bytes,
                content_type='audio/mpeg'
            )
            
            # Make blob public (or use signed URLs for security)
            blob.make_public()
            
            # Get public URL
            public_url = blob.public_url
            
            logger.info(f"Podcast uploaded successfully for user {user_id}: {blob_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading podcast for user {user_id}: {str(e)}")
            return None
    
    async def delete_old_files(self, user_id: str, days_old: int = 30):
        """
        Delete old files for a user (cleanup task)
        Args:
            user_id: User ID
            days_old: Delete files older than this many days
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            
            # List and delete old images
            image_prefix = f"{settings.IMAGES_FOLDER}/{user_id}/"
            podcast_prefix = f"{settings.PODCASTS_FOLDER}/{user_id}/"
            
            deleted_count = 0
            
            for prefix in [image_prefix, podcast_prefix]:
                blobs = self.client.list_blobs(self.bucket, prefix=prefix)
                
                for blob in blobs:
                    # Extract date from path (assumes format: folder/userid/YYYY-MM-DD/file)
                    path_parts = blob.name.split('/')
                    if len(path_parts) >= 3:
                        file_date = path_parts[2]  # YYYY-MM-DD
                        if file_date < cutoff_str:
                            blob.delete()
                            deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old files for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting old files for user {user_id}: {str(e)}")
    
    def get_bucket_info(self) -> dict:
        """Get bucket information for debugging"""
        try:
            return {
                "bucket_name": self.bucket.name,
                "project": settings.PROJECT_ID,
                "location": self.bucket.location,
                "storage_class": self.bucket.storage_class
            }
        except Exception as e:
            logger.error(f"Error getting bucket info: {str(e)}")
            return {"error": str(e)}