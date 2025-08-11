import logging
from typing import Optional
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from config.settings import settings

logger = logging.getLogger(__name__)

class ImagenService:
    """Service for Vertex AI Image Generation"""
    
    def __init__(self):
        self.model = None
        self._initialize_imagen()
    
    def _initialize_imagen(self):
        """Initialize Vertex AI Image Generation"""
        try:
            vertexai.init(
                project=settings.PROJECT_ID,
                location=settings.VERTEX_AI_LOCATION
            )
            
            self.model = ImageGenerationModel.from_pretrained(settings.IMAGEN_MODEL)
            logger.info("Vertex AI Imagen initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Vertex AI Imagen: {str(e)}")
            raise
    
    async def generate_image(self, prompt: str, user_id: str) -> Optional[bytes]:
        """
        Generate image from text prompt
        Returns: Image bytes or None if error
        """
        try:
            logger.info(f"Generating image for user {user_id} with prompt length: {len(prompt)}")
            
            # Generate image
            images = self.model.generate_images(
                prompt=prompt,
                number_of_images=1,
                language="en",  # Imagen API works better with English prompts
                aspect_ratio="1:1",
                safety_filter_level="allow_most",
                person_generation="allow_adult"
            )
            
            if images and len(images) > 0:
                # Get the first (and only) generated image
                image = images[0]
                
                # Convert to bytes
                image_bytes = image._image_bytes
                
                logger.info(f"Image generated successfully for user {user_id}")
                return image_bytes
            else:
                logger.warning(f"No images generated for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image for user {user_id}: {str(e)}")
            # Don't raise exception, return None to continue processing
            return None
    
    def _translate_prompt_to_english(self, spanish_prompt: str) -> str:
        """
        Simple translation helper for common Spanish terms
        Vertex AI Imagen works better with English prompts
        """
        # Basic translation mapping - you can enhance this
        translations = {
            "una persona": "a person",
            "persona": "person",
            "hombre": "man",
            "mujer": "woman",
            "niño": "child",
            "casa": "house",
            "paisaje": "landscape",
            "naturaleza": "nature",
            "ciudad": "city",
            "playa": "beach",
            "montaña": "mountain",
            "sol": "sun",
            "luna": "moon",
            "estrella": "star",
            "árbol": "tree",
            "flor": "flower",
            "agua": "water",
            "fuego": "fire",
            "cielo": "sky",
            "nube": "cloud",
            "colorido": "colorful",
            "hermoso": "beautiful",
            "artístico": "artistic",
            "moderno": "modern",
            "vintage": "vintage",
            "realista": "realistic",
            "abstracto": "abstract"
        }
        
        english_prompt = spanish_prompt.lower()
        
        for spanish, english in translations.items():
            english_prompt = english_prompt.replace(spanish, english)
        
        return english_prompt
    
    async def generate_image_with_translation(self, spanish_prompt: str, user_id: str) -> Optional[bytes]:
        """
        Generate image with automatic Spanish to English translation
        """
        try:
            # Try with original prompt first
            image_bytes = await self.generate_image(spanish_prompt, user_id)
            
            if image_bytes:
                return image_bytes
            
            # If failed, try with translated prompt
            english_prompt = self._translate_prompt_to_english(spanish_prompt)
            logger.info(f"Retrying with translated prompt for user {user_id}")
            
            return await self.generate_image(english_prompt, user_id)
            
        except Exception as e:
            logger.error(f"Error in generate_image_with_translation for user {user_id}: {str(e)}")
            return # services/imagen_service.py
import logging
from typing import Optional

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

logger = logging.getLogger(__name__)


class ImagenService:
    """
    Servicio para generar imágenes con Vertex AI Imagen.
    Requisitos:
      - variable de entorno GOOGLE_CLOUD_PROJECT (o vertexai.init ya llamado en app)
      - google-cloud-aiplatform instalado
      - StorageService con método upload_bytes(bytes, dest_path, content_type) -> str
    """

    def __init__(
        self,
        storage_service,
        location: Optional[str] = None,
        project: Optional[str] = None,
        model_name: str = "imagen-3.0-generate-002",
    ) -> None:
        # Si app ya llamó vertexai.init, esto es no-op. Si no, permite override.
        if project or location:
            vertexai.init(project=project, location=location)

        self.storage = storage_service
        self.model = ImageGenerationModel.from_pretrained(model_name)
        logger.info("Vertex AI Imagen initialized successfully")

    # -------- helpers internos --------
    def _extract_image_bytes(self, resp) -> bytes:
        """
        Extrae los bytes PNG de la primera imagen devuelta por Imagen.
        Maneja las variaciones del SDK.
        """
        images = getattr(resp, "images", None)
        if not images or len(images) == 0:
            raise RuntimeError("Imagen no regresó imágenes")

        img0 = images[0]

        # 1) Campo directo en builds recientes
        image_bytes = getattr(img0, "image_bytes", None) or getattr(img0, "_image_bytes", None)
        if image_bytes is not None:
            return image_bytes

        # 2) Método conversor en algunos builds
        to_bytes = getattr(img0, "to_bytes", None) or getattr(img0, "_to_bytes", None)
        if callable(to_bytes):
            return to_bytes()

        raise RuntimeError("No pude extraer bytes de la imagen devuelta por Imagen")

    # -------- API pública --------
    def generate_image_for_user(
        self,
        user_id: str,
        prompt: str,
        *,
        out_path: Optional[str] = None,
        image_format: str = "png",
        number_of_images: int = 1,
        add_watermark: bool = False,
        safety_filter_level: str = "block_some",
        aspect_ratio: Optional[str] = None,  # p.ej. "1:1", "16:9" (si tu build lo soporta)
    ) -> str:
        """
        Genera una imagen a partir de un prompt, sube a GCS y regresa el URI.
        Retorna: GCS URI (o URL firmada dependiendo de tu StorageService)
        """
        if not out_path:
            out_path = f"retodia/images/{user_id}.{image_format}"

        logger.info(
            "Generating image for user %s with prompt length: %s",
            user_id,
            len(prompt or ""),
        )

        # Llamada a Imagen
        resp = self.model.generate_images(
            prompt=prompt,
            number_of_images=number_of_images,
            add_watermark=add_watermark,
            # Algunos campos pueden no existir en todos los releases; coméntalos si no aplican
            safety_filter_level=safety_filter_level,
            # aspect_ratio=aspect_ratio,
        )

        # OJO: NO usar len(resp) (rompe). Validar por imágenes:
        if not getattr(resp, "images", None):
            raise RuntimeError("Imagen no generó resultados")

        image_bytes = self._extract_image_bytes(resp)

        # Subir a Cloud Storage
        uri = self.storage.upload_bytes(
            image_bytes,
            dest_path=out_path,
            content_type=f"image/{image_format}",
        )
        logger.info("Image uploaded successfully for user %s -> %s", user_id, uri)
        return uri

    def generate_image_with_translation_fallback(
        self,
        user_id: str,
        prompt_es: str,
        prompt_en: str,
        *,
        out_path: Optional[str] = None,
    ) -> str:
        """
        Intenta generar con prompt_es; si falla por contenido/len, reintenta con prompt_en.
        """
        try:
            return self.generate_image_for_user(user_id, prompt_es, out_path=out_path)
        except Exception as e:
            logger.error(
                "Error generating image (ES) for user %s: %s. Retrying with EN...",
                user_id,
                e,
            )
            return self.generate_image_for_user(user_id, prompt_en, out_path=out_path)
