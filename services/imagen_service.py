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
            return None