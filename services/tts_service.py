import logging
import os
import mimetypes
import struct
from typing import Optional
from google import genai
from google.genai import types
from config.settings import settings

logger = logging.getLogger(__name__)

class TTSService:
    """Service for Gemini 2.5 Pro TTS - Based on official Google example"""
    
    def __init__(self):
        self.client = None
        self._initialize_gemini_tts()
    
    def _initialize_gemini_tts(self):
        """Initialize Gemini TTS client"""
        try:
            api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in settings or environment")
            
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini TTS initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Gemini TTS: {str(e)}")
            raise
