# services/imagen_service.py
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
