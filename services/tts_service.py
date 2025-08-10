import logging
from typing import Optional
from google.cloud import texttospeech
import random
from config.settings import settings

logger = logging.getLogger(__name__)

class TTSService:
    """Service for Google Cloud Text-to-Speech"""
    
    def __init__(self):
        self.client = None
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize Cloud Text-to-Speech client"""
        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("Cloud TTS initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Cloud TTS: {str(e)}")
            raise
    
    def _get_voice_config(self, use_female: bool = None) -> texttospeech.VoiceSelectionParams:
        """
        Get voice configuration for TTS
        Args:
            use_female: If True, use female voice. If False, use male. If None, random.
        """
        if use_female is None:
            use_female = random.choice([True, False])
        
        voice_name = settings.TTS_VOICE_FEMALE if use_female else settings.TTS_VOICE_MALE
        
        return texttospeech.VoiceSelectionParams(
            language_code=settings.TTS_LANGUAGE,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE if use_female else texttospeech.SsmlVoiceGender.MALE
        )
    
    def _get_audio_config(self) -> texttospeech.AudioConfig:
        """Get audio configuration for podcast quality"""
        return texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,  # Normal speaking rate
            pitch=0.0,         # Normal pitch
            volume_gain_db=0.0, # Normal volume
            sample_rate_hertz=24000,  # High quality for podcasts
            effects_profile_id=["telephony-class-application"]  # Enhanced audio quality
        )
    
    async def generate_podcast_audio(self, script: str, user_id: str, use_female: bool = None) -> Optional[bytes]:
        """
        Generate podcast audio from script
        Args:
            script: Text script to convert to speech
            user_id: User ID for logging
            use_female: Voice gender preference
        Returns:
            Audio bytes (MP3) or None if error
        """
        try:
            logger.info(f"Generating podcast audio for user {user_id}, script length: {len(script)}")
            
            # Prepare the text (add SSML if needed for more natural speech)
            ssml_text = self._prepare_ssml_text(script)
            
            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
            
            # Get voice and audio configurations
            voice = self._get_voice_config(use_female)
            audio_config = self._get_audio_config()
            
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            logger.info(f"Podcast audio generated successfully for user {user_id}")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Error generating podcast audio for user {user_id}: {str(e)}")
            return None
    
    def _prepare_ssml_text(self, text: str) -> str:
        """
        Prepare text with SSML tags for more natural speech
        Adds pauses, emphasis, and natural breaks for podcast-like delivery
        """
        try:
            # Clean the text
            clean_text = text.replace('"', '&quot;').replace("'", '&apos;')
            clean_text = clean_text.replace('<', '&lt;').replace('>', '&gt;')
            
            # Add natural breaks for better flow
            clean_text = self._add_natural_breaks(clean_text)
            
            # Add SSML structure for natural podcast delivery
            ssml = f"""
            <speak>
                <prosody rate="medium" pitch="0st" volume="medium">
                    <break time="500ms"/>
                    {clean_text}
                    <break time="1s"/>
                </prosody>
            </speak>
            """
            
            return ssml.strip()
            
        except Exception as e:
            logger.error(f"Error preparing SSML text: {str(e)}")
            # Return plain text if SSML preparation fails
            return text
    
    def _add_natural_breaks(self, text: str) -> str:
        """Add natural breaks to text for better podcast flow"""
        # Add pauses after punctuation for more natural speech
        text = text.replace('. ', '. <break time="300ms"/>')
        text = text.replace('? ', '? <break time="400ms"/>')
        text = text.replace('! ', '! <break time="400ms"/>')
        text = text.replace(', ', ', <break time="200ms"/>')
        text = text.replace(': ', ': <break time="250ms"/>')
        text = text.replace('; ', '; <break time="250ms"/>')
        
        # Add emphasis to the user's name when it appears
        text = text.replace('{{nombre}}', '<emphasis level="moderate">{{nombre}}</emphasis>')
        
        return text
    
    async def test_voice_generation(self, user_id: str) -> dict:
        """
        Test voice generation with both male and female voices
        Returns: Test results
        """
        try:
            test_script = f"Hola, este es un test de audio para el usuario {user_id}. ¿Puedes escuchar esto claramente?"
            
            results = {}
            
            # Test female voice
            female_audio = await self.generate_podcast_audio(test_script, user_id, use_female=True)
            results['female_voice'] = {
                'success': female_audio is not None,
                'size_bytes': len(female_audio) if female_audio else 0
            }
            
            # Test male voice  
            male_audio = await self.generate_podcast_audio(test_script, user_id, use_female=False)
            results['male_voice'] = {
                'success': male_audio is not None,
                'size_bytes': len(male_audio) if male_audio else 0
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error testing voice generation: {str(e)}")
            return {'error': str(e)}