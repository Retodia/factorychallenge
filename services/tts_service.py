import logging
from typing import Optional, List
from google.cloud import texttospeech
import random
import re
import io
from pydub import AudioSegment
from config.settings import settings

logger = logging.getLogger(__name__)

class TTSService:
    """Service for Google Cloud Text-to-Speech with chunking support"""
    
    def __init__(self):
        self.client = None
        self.max_chunk_bytes = 4500  # Safe limit under 5000 bytes
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
    
    def _chunk_text_safely(self, text: str) -> List[str]:
        """
        Chunk text safely by sentences, keeping under byte limit
        """
        chunks = []
        
        # Split by sentences (keeping sentence markers)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        for sentence in sentences:
            # Test if adding this sentence would exceed limit
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            # Create SSML wrapper to test real size
            test_ssml = f'<speak><prosody rate="medium">{test_chunk}</prosody></speak>'
            
            if len(test_ssml.encode('utf-8')) < self.max_chunk_bytes:
                current_chunk = test_chunk
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _create_chunk_ssml(self, text_chunk: str, chunk_index: int, use_female: bool = None) -> str:
        """Create SSML for a text chunk with proper formatting"""
        try:
            # Clean the text
            clean_text = text_chunk.replace('"', '&quot;').replace("'", '&apos;')
            clean_text = clean_text.replace('<', '&lt;').replace('>', '&gt;')
            
            # Add natural breaks
            clean_text = self._add_natural_breaks(clean_text)
            
            # Add pause for chunks 2+ to smooth transitions
            initial_break = '<break time="300ms"/>' if chunk_index > 0 else '<break time="500ms"/>'
            
            # Create SSML with consistent voice settings
            ssml = f"""
            <speak>
                <prosody rate="medium" pitch="0st" volume="medium">
                    {initial_break}
                    {clean_text}
                    <break time="200ms"/>
                </prosody>
            </speak>
            """
            
            return ssml.strip()
            
        except Exception as e:
            logger.error(f"Error creating chunk SSML: {str(e)}")
            # Fallback to simple SSML
            return f'<speak>{text_chunk}</speak>'
    
    async def generate_podcast_audio(self, script: str, user_id: str, use_female: bool = None) -> Optional[bytes]:
        """
        Generate podcast audio from script with chunking support
        Args:
            script: Text script to convert to speech
            user_id: User ID for logging
            use_female: Voice gender preference
        Returns:
            Audio bytes (MP3) or None if error
        """
        try:
            logger.info(f"Generating podcast audio for user {user_id}, script length: {len(script)}")
            
            # Check if we need chunking
            simple_ssml = self._prepare_ssml_text(script)
            if len(simple_ssml.encode('utf-8')) < self.max_chunk_bytes:
                # Small enough, process normally
                return await self._generate_single_audio(simple_ssml, user_id, use_female)
            
            # Need chunking
            logger.info(f"Script too large, using chunking for user {user_id}")
            return await self._generate_chunked_audio(script, user_id, use_female)
            
        except Exception as e:
            logger.error(f"Error generating podcast audio for user {user_id}: {str(e)}")
            return None
    
    async def _generate_single_audio(self, ssml_text: str, user_id: str, use_female: bool = None) -> Optional[bytes]:
        """Generate audio for single chunk"""
        try:
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
            voice = self._get_voice_config(use_female)
            audio_config = self._get_audio_config()
            
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            logger.info(f"Single audio generated successfully for user {user_id}")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Error generating single audio for user {user_id}: {str(e)}")
            return None
    
    async def _generate_chunked_audio(self, script: str, user_id: str, use_female: bool = None) -> Optional[bytes]:
        """Generate audio using chunking"""
        try:
            # Split into chunks
            text_chunks = self._chunk_text_safely(script)
            logger.info(f"Split into {len(text_chunks)} chunks for user {user_id}")
            
            audio_segments = []
            voice = self._get_voice_config(use_female)
            audio_config = self._get_audio_config()
            
            # Process each chunk
            for i, text_chunk in enumerate(text_chunks):
                chunk_ssml = self._create_chunk_ssml(text_chunk, i, use_female)
                
                # Validate chunk size
                chunk_bytes = len(chunk_ssml.encode('utf-8'))
                logger.info(f"Processing chunk {i+1}/{len(text_chunks)} ({chunk_bytes} bytes) for user {user_id}")
                
                try:
                    synthesis_input = texttospeech.SynthesisInput(ssml=chunk_ssml)
                    
                    response = self.client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    if response.audio_content:
                        audio_segments.append(response.audio_content)
                        logger.info(f"Chunk {i+1} processed successfully for user {user_id}")
                    
                except Exception as chunk_error:
                    logger.error(f"Error processing chunk {i+1} for user {user_id}: {str(chunk_error)}")
                    # Continue with other chunks
                    continue
            
            if not audio_segments:
                logger.error(f"No audio segments generated for user {user_id}")
                return None
            
            # Concatenate audio segments
            return self._concatenate_audio_segments(audio_segments, user_id)
            
        except Exception as e:
            logger.error(f"Error in chunked audio generation for user {user_id}: {str(e)}")
            return None
    
    def _concatenate_audio_segments(self, audio_segments: List[bytes], user_id: str) -> Optional[bytes]:
        """Concatenate multiple audio segments into one"""
        try:
            if len(audio_segments) == 1:
                return audio_segments[0]
            
            # Convert first segment
            combined = AudioSegment.from_mp3(io.BytesIO(audio_segments[0]))
            
            # Add remaining segments with small crossfade
            for audio_bytes in audio_segments[1:]:
                segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                combined = combined.append(segment, crossfade=100)  # 100ms crossfade
            
            # Export as MP3
            output_buffer = io.BytesIO()
            combined.export(output_buffer, format="mp3", bitrate="128k")
            
            logger.info(f"Audio concatenation successful for user {user_id}")
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error concatenating audio for user {user_id}: {str(e)}")
            # Fallback: return first segment if concatenation fails
            return audio_segments[0] if audio_segments else None
    
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
