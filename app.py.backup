from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import logging
from handlers.prompt1_handler import handle_daily_prompt
from handlers.firestore_triggers import handle_firestore_trigger
from utils.logger import setup_logger

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)

app = FastAPI(title="Challenge Factory - Retos Diarios", version="1.0.0")

class SchedulerRequest(BaseModel):
    """Request model for scheduler endpoint"""
    user_id: Optional[str] = None  # If None, process all users

class FirestoreTrigger(BaseModel):
    """Request model for Firestore trigger"""
    user_id: str
    document_id: str
    action: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "OK", "service": "Challenge Factory API"}

@app.get("/health")
async def health_check():
    """Health check for Cloud Run"""
    return {"status": "healthy", "service": "challenge-factory"}

@app.post("/trigger-daily")
async def trigger_daily_retos(
    request: SchedulerRequest, 
    background_tasks: BackgroundTasks
):
    """
    Endpoint triggered by Cloud Scheduler
    Generates daily challenges for users
    """
    try:
        logger.info(f"Daily trigger received for user: {request.user_id}")
        
        # Run in background to avoid timeout
        background_tasks.add_task(handle_daily_prompt, request.user_id)
        
        return {
            "status": "success", 
            "message": "Daily challenge generation started",
            "user_id": request.user_id
        }
        
    except Exception as e:
        logger.error(f"Error in daily trigger: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/firestore-webhook")
async def firestore_webhook(
    trigger: FirestoreTrigger,
    background_tasks: BackgroundTasks
):
    """
    Webhook for Firestore triggers
    Handles updates to retosdiarios collection
    """
    try:
        logger.info(f"Firestore trigger: {trigger.action} for user {trigger.user_id}")
        
        if trigger.action == "update":
            # Process the three additional prompts
            background_tasks.add_task(
                handle_firestore_trigger, 
                trigger.user_id, 
                trigger.document_id
            )
            
            return {
                "status": "success",
                "message": "Processing additional prompts",
                "user_id": trigger.user_id,
                "document_id": trigger.document_id
            }
        
        return {"status": "ignored", "action": trigger.action}
        
    except Exception as e:
        logger.error(f"Error in Firestore webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test/{user_id}")
async def test_user_data(user_id: str):
    """Test endpoint to verify user data retrieval"""
    try:
        from services.firestore_service import FirestoreService
        fs = FirestoreService()
        
        user_data = await fs.get_user_data(user_id)
        return {"user_id": user_id, "data": user_data}
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)