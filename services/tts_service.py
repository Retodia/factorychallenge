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
    
    async def generate_podcast_audio(self, script: str, user_id: str, use_female: bool = None) -> Optional[bytes]:
        """Generate podcast audio using official Gemini TTS syntax"""
        try:
            logger.info(f"Generating podcast audio with Gemini for user {user_id}, script length: {len(script)}")
            
            # Convert Speaker 1/Speaker 2 for Gemini
            processed_script = script.replace("Speaker 1:", "Mario:")
            processed_script = processed_script.replace("Speaker 2:", "Vale:")
            
            # Use official Google format
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"Read aloud in a natural, conversational podcast tone:\n\n{processed_script}"),
                    ],
                ),
            ]
            
            # Official configuration syntax
            generate_content_config = types.GenerateContentConfig(
                temperature=0.8,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="Mario",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Zephyr"
                                    )
                                ),
                            ),
                            types.SpeakerVoiceConfig(
                                speaker="Vale",
                                voice_config=types.VoiceConfig(
