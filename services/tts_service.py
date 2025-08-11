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
    """Service for Gemini 2.5 Pro TTS with multi-speaker support"""
    
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
        """
        Generate podcast audio using Gemini 2.5 Pro TTS
        Args:
            script: Dialogue script with Speaker 1/Speaker 2 format
            user_id: User ID for logging
            use_female: Not used (Gemini handles multi-speaker automatically)
        Returns:
            Audio bytes (WAV) or None if error
        """
        try:
            logger.info(f"Generating podcast audio with Gemini for user {user_id}, script length: {len(script)}")
            
            # Prepare content for Gemini
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"Read aloud in a natural, conversational tone:\n\n{script}"),
                    ],
                ),
            ]
            
            # Configure generation with multi-speaker
            generate_content_config = types.GenerateContentConfig(
                temperature=0.8,  # Slightly creative but consistent
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="Speaker 1",  # MARIO
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Sage"  # Warm, masculine voice
                                    )
                                ),
                            ),
                            types.SpeakerVoiceConfig(
                                speaker="Speaker 2",  # VALE
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Aoede"  # Clear, feminine voice
                                    )
                                ),
                            ),
                        ]
                    ),
                ),
            )
            
            # Generate audio in streaming chunks
            audio_chunks = []
            
            for chunk in self.client.models.generate_content_stream(
                model="gemini-2.5-pro-preview-tts",
                contents=contents,
                config=generate_content_config,
            ):
                if (
                    chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue
                
                # Check for audio data
                if (chunk.candidates[0].content.parts[0].inline_data and 
                    chunk.candidates[0].content.parts[0].inline_data.data):
                    
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    data_buffer = inline_data.data
                    
                    # Convert to WAV if needed
                    if inline_data.mime_type != "audio/wav":
                        data_buffer = self._convert_to_wav(inline_data.data, inline_data.mime_type)
                    
                    audio_chunks.append(data_buffer)
                    logger.info(f"Received audio chunk for user {user_id}, size: {len(data_buffer)} bytes")
            
            if not audio_chunks:
                logger.error(f"No audio chunks generated for user {user_id}")
                return None
            
            # Combine all chunks
            final_audio = b''.join(audio_chunks)
            logger.info(f"Podcast audio generated successfully for user {user_id}, final size: {len(final_audio)} bytes")
            
            return final_audio
            
        except Exception as e:
            logger.error(f"Error generating podcast audio for user {user_id}: {str(e)}")
            return None
    
    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Convert audio data to WAV format"""
        try:
            parameters = self._parse_audio_mime_type(mime_type)
            bits_per_sample = parameters["bits_per_sample"]
            sample_rate = parameters["rate"]
            num_channels = 1
            data_size = len(audio_data)
            bytes_per_sample = bits_per_sample // 8
            block_align = num_channels * bytes_per_sample
            byte_rate = sample_rate * block_align
            chunk_size = 36 + data_size
            
            header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",          # ChunkID
                chunk_size,       # ChunkSize
                b"WAVE",          # Format
                b"fmt ",          # Subchunk1ID
                16,               # Subchunk1Size (16 for PCM)
                1,                # AudioFormat (1 for PCM)
                num_channels,     # NumChannels
                sample_rate,      # SampleRate
                byte_rate,        # ByteRate
                block_align,      # BlockAlign
                bits_per_sample,  # BitsPerSample
                b"data",          # Subchunk2ID
                data_size         # Subchunk2Size
            )
            return header + audio_data
            
        except Exception as e:
            logger.error(f"Error converting audio to WAV: {str(e)}")
            return audio_data  # Return original if conversion fails
    
    def _parse_audio_mime_type(self, mime_type: str) -> dict:
        """Parse audio MIME type parameters"""
        bits_per_sample = 16
        rate = 24000
        
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate_str = param.split("=", 1)[1]
                    rate = int(rate_str)
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass
        
        return {"bits_per_sample": bits_per_sample, "rate": rate}
    
    async def test_voice_generation(self, user_id: str) -> dict:
        """Test voice generation with Gemini TTS"""
        try:
            test_script = f"Speaker 1: Hola, este es un test de audio para el usuario {user_id}.\nSpeaker 2: ¿Puedes escuchar esto claramente? La calidad debería ser excelente."
            
            audio = await self.generate_podcast_audio(test_script, user_id)
            
            return {
                'success': audio is not None,
                'size_bytes': len(audio) if audio else 0,
                'service': 'Gemini 2.5 Pro TTS'
            }
            
        except Exception as e:
            logger.error(f"Error testing Gemini TTS: {str(e)}")
            return {'error': str(e)}
