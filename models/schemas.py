"""Pydantic models for request/response validation"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SchedulerRequest(BaseModel):
    """Request model for scheduler endpoint"""
    user_id: Optional[str] = Field(None, description="Specific user ID to process. If None, process all users")
    force_regenerate: Optional[bool] = Field(False, description="Force regenerate even if already exists today")

class FirestoreTrigger(BaseModel):
    """Request model for Firestore trigger"""
    user_id: str = Field(..., description="User ID")
    document_id: str = Field(..., description="Document ID in retosdiarios collection")
    action: str = Field(..., description="Action type: create, update, delete")

class UserDataResponse(BaseModel):
    """Response model for user data"""
    userid: str
    nombre: Optional[str] = None
    d1: Optional[str] = None
    d2: Optional[str] = None
    d3: Optional[str] = None
    d4: Optional[str] = None
    email: Optional[str] = None
    avances: Optional[List[str]] = []

class RetoDiarioResponse(BaseModel):
    """Response model for reto diario"""
    id: str
    userid: str
    brief: Optional[str] = None
    fecha: Optional[str] = None
    retodia: Optional[str] = None
    retoimagen: Optional[str] = None
    retopodcast: Optional[str] = None
    timestamp: Optional[datetime] = None

class ProcessingResult(BaseModel):
    """Model for processing results"""
    success: bool
    message: str
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class BatchProcessingResult(BaseModel):
    """Model for batch processing results"""
    total: int
    successful: int
    failed: int
    success_rate: str
    details: Optional[List[ProcessingResult]] = None

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    timestamp: datetime
    version: str = "1.0.0"

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None

class ServiceStatus(BaseModel):
    """Service status model"""
    service_name: str
    status: str  # healthy, unhealthy, unknown
    last_check: datetime
    details: Optional[Dict[str, Any]] = None

class SystemStatus(BaseModel):
    """System status model"""
    overall_status: str
    services: List[ServiceStatus]
    last_updated: datetime