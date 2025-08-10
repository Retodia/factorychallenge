import logging
import asyncio
from typing import List, Optional
from services.firestore_service import FirestoreService
from services.vertex_ai_service import VertexAIService
from config.settings import settings  # ← AGREGAR ESTA LÍNEA

logger = logging.getLogger(__name__)

class Prompt1Handler:
    """Handler for daily challenge generation (Prompt 1)"""
    
    def __init__(self):
        self.firestore_service = FirestoreService()
        self.vertex_ai_service = VertexAIService()
    
    async def process_single_user(self, user_id: str) -> bool:
        """
        Process daily challenge for a single user
        Returns: True if successful, False otherwise
        """
        try:
            logger.info(f"Starting daily challenge generation for user {user_id}")
            
            # 1. Get user data from all relevant collections
            user_data = await self.firestore_service.get_user_data(user_id)
            
            if not user_data:
                logger.warning(f"No data found for user {user_id}")
                return False
            
            # 2. Generate brief using prompt1
            brief = await self.vertex_ai_service.generate_brief(user_data)
            
            if not brief:
                logger.error(f"Failed to generate brief for user {user_id}")
                return False
            
            # 3. Save brief to retosdiarios collection
            doc_id = await self.firestore_service.create_reto_diario(user_id, brief)
            
            logger.info(f"Daily challenge created successfully for user {user_id}, doc_id: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {str(e)}")
            return False
    
    async def process_all_users(self) -> dict:
        """
        Process daily challenges for all active users
        Returns: Summary of results
        """
        try:
            logger.info("Starting daily challenge generation for all users")
            
            # Get all active users
            user_ids = await self.firestore_service.get_all_active_users()
            
            if not user_ids:
                logger.warning("No active users found")
                return {"total": 0, "successful": 0, "failed": 0}
            
            logger.info(f"Found {len(user_ids)} active users")
            
            # Process users in batches to avoid overwhelming the system
            batch_size = settings.MAX_CONCURRENT_USERS
            successful = 0
            failed = 0
            
            for i in range(0, len(user_ids), batch_size):
                batch = user_ids[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: users {i+1}-{min(i+batch_size, len(user_ids))}")
                
                # Process batch concurrently
                tasks = [self.process_single_user(user_id) for user_id in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                for result in results:
                    if isinstance(result, Exception):
                        failed += 1
                        logger.error(f"Batch processing exception: {str(result)}")
                    elif result:
                        successful += 1
                    else:
                        failed += 1
                
                # Small delay between batches
                if i + batch_size < len(user_ids):
                    await asyncio.sleep(2)
            
            summary = {
                "total": len(user_ids),
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful/len(user_ids)*100):.1f}%" if user_ids else "0%"
            }
            
            logger.info(f"Daily challenge generation completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in process_all_users: {str(e)}")
            raise

# Main handler function for app.py
async def handle_daily_prompt(user_id: Optional[str] = None):
    """
    Main handler function called from FastAPI endpoint
    Args:
        user_id: If provided, process only this user. If None, process all users.
    """
    try:
        handler = Prompt1Handler()
        
        if user_id:
            logger.info(f"Processing daily prompt for specific user: {user_id}")
            success = await handler.process_single_user(user_id)
            
            if success:
                logger.info(f"Daily prompt completed successfully for user {user_id}")
            else:
                logger.error(f"Daily prompt failed for user {user_id}")
        else:
            logger.info("Processing daily prompt for all users")
            summary = await handler.process_all_users()
            logger.info(f"Daily prompt batch completed: {summary}")
            
    except Exception as e:
        logger.error(f"Error in handle_daily_prompt: {str(e)}")
        raise
