import logging
import asyncio
from typing import Dict, Any
from services.firestore_service import FirestoreService
from services.vertex_ai_service import VertexAIService
from services.imagen_service import ImagenService
from services.tts_service import TTSService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)

class FirestoreTriggersHandler:
    """Handler for Firestore triggers - processes prompts 2, 3, 4"""
    
    def __init__(self):
        self.firestore_service = FirestoreService()
        self.vertex_ai_service = VertexAIService()
        self.storage_service = StorageService()  # ✅ CREAR PRIMERO
        self.imagen_service = ImagenService(self.storage_service, model_name="imagen-3.0-generate-002")  # ✅ PASAR storage_service
        self.tts_service = TTSService(self.storage_service)  # ✅ PASAR storage_service
    
    async def process_reto_dia(self, user_data: Dict[str, Any], doc_id: str) -> bool:
        """Process prompt 2 - Generate reto del día"""
        try:
            logger.info(f"Generating reto dia for user {user_data['userid']}")
            
            reto_dia = await self.vertex_ai_service.generate_reto_dia(user_data)
            
            if reto_dia:
                await self.firestore_service.update_reto_diario(doc_id, {
                    'retodia': reto_dia
                })
                logger.info(f"Reto dia updated successfully for user {user_data['userid']}")
                return True
            else:
                logger.error(f"Failed to generate reto dia for user {user_data['userid']}")
                return False
                
        except Exception as e:
            logger.error(f"Error in process_reto_dia: {str(e)}")
            return False
    
    async def process_imagen(self, user_data: Dict[str, Any], doc_id: str) -> bool:
        """Process prompt 3 - Generate image"""
        try:
            logger.info(f"Generating image for user {user_data['userid']}")
            
            # 1. Generate image description prompt
            imagen_prompt = await self.vertex_ai_service.generate_imagen_prompt(user_data)
            
            if not imagen_prompt:
                logger.error(f"Failed to generate image prompt for user {user_data['userid']}")
                return False
            
            # 2. Generate actual image
            image_bytes = await self.imagen_service.generate_image_with_translation(
                imagen_prompt, 
                user_data['userid']
            )
            
            if not image_bytes:
                logger.error(f"Failed to generate image for user {user_data['userid']}")
                return False
            
            # 3. Upload to Cloud Storage
            image_url = await self.storage_service.upload_image(
                image_bytes, 
                user_data['userid']
            )
            
            if not image_url:
                logger.error(f"Failed to upload image for user {user_data['userid']}")
                return False
            
            # 4. Update Firestore with image URL
            await self.firestore_service.update_reto_diario(doc_id, {
                'retoimagen': image_url
            })
            
            logger.info(f"Image process completed successfully for user {user_data['userid']}")
            return True
            
        except Exception as e:
            logger.error(f"Error in process_imagen: {str(e)}")
            return False
    
    async def process_podcast(self, user_data: Dict[str, Any], doc_id: str) -> bool:
        """Process prompt 4 - Generate podcast"""
        try:
            logger.info(f"Generating podcast for user {user_data['userid']}")
            
            # 1. Generate podcast script
            podcast_script = await self.vertex_ai_service.generate_podcast_script(user_data)
            
            if not podcast_script:
                logger.error(f"Failed to generate podcast script for user {user_data['userid']}")
                return False
            
            # 2. Convert script to audio
            audio_bytes = await self.tts_service.generate_podcast_audio(
                podcast_script,
                user_data['userid']
            )
            
            if not audio_bytes:
                logger.error(f"Failed to generate podcast audio for user {user_data['userid']}")
                return False
            
            # 3. Upload to Cloud Storage
            podcast_url = await self.storage_service.upload_podcast(
                audio_bytes,
                user_data['userid']
            )
            
            if not podcast_url:
                logger.error(f"Failed to upload podcast for user {user_data['userid']}")
                return False
            
            # 4. Update Firestore with podcast URL
            await self.firestore_service.update_reto_diario(doc_id, {
                'retopodcast': podcast_url
            })
            
            logger.info(f"Podcast process completed successfully for user {user_data['userid']}")
            return True
            
        except Exception as e:
            logger.error(f"Error in process_podcast: {str(e)}")
            return False
    
    async def process_all_prompts(self, user_id: str, doc_id: str) -> dict:
        """
        Process all three prompts (2, 3, 4) in parallel
        Returns: Summary of results
        """
        try:
            logger.info(f"Starting all prompts processing for user {user_id}, doc {doc_id}")
            
            # Get user data
            user_data = await self.firestore_service.get_user_data(user_id)
            if not user_data:
                logger.error(f"No user data found for {user_id}")
                return {"success": False, "error": "User data not found"}
            
            # Get reto diario data (includes brief)
            reto_data = await self.firestore_service.get_reto_diario(doc_id)
            if not reto_data:
                logger.error(f"Reto diario {doc_id} not found")
                return {"success": False, "error": "Reto diario not found"}
            
            # Add brief to user data for subsequent prompts
            user_data['brief'] = reto_data.get('brief', '')
            
            # Run all three processes in parallel
            tasks = [
                self.process_reto_dia(user_data, doc_id),
                self.process_imagen(user_data, doc_id),
                self.process_podcast(user_data, doc_id)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_tasks = sum(1 for result in results if result is True)
            failed_tasks = len(results) - successful_tasks
            
            summary = {
                "success": successful_tasks > 0,
                "total_tasks": len(tasks),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "reto_dia": results[0] if not isinstance(results[0], Exception) else False,
                "imagen": results[1] if not isinstance(results[1], Exception) else False,
                "podcast": results[2] if not isinstance(results[2], Exception) else False
            }
            
            logger.info(f"All prompts processing completed for user {user_id}: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in process_all_prompts: {str(e)}")
            return {"success": False, "error": str(e)}

# Main handler function for app.py
async def handle_firestore_trigger(user_id: str, doc_id: str):
    """
    Main handler function called from FastAPI endpoint
    Triggered when retosdiarios is updated with brief
    """
    try:
        logger.info(f"Firestore trigger handler started for user {user_id}, doc {doc_id}")
        
        handler = FirestoreTriggersHandler()
        result = await handler.process_all_prompts(user_id, doc_id)
        
        if result.get("success"):
            logger.info(f"Firestore trigger completed successfully for user {user_id}")
        else:
            logger.error(f"Firestore trigger failed for user {user_id}: {result}")
            
    except Exception as e:
        logger.error(f"Error in handle_firestore_trigger: {str(e)}")
        raise