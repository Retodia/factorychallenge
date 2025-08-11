# services/tts_service.py
import io
import wave
import logging
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class TTSService:
    """
    Servicio de TTS con Gemini (google-genai).
    Requisitos:
      - GOOGLE_API_KEY en el entorno (o pasar api_key al constructor)
      - StorageService con upload_bytes(bytes, dest_path, content_type) -> str
    """

    def __init__(self, storage_service, api_key: Optional[str] = None) -> None:
        self.client = genai.Client(api_key=api_key)
        self.storage = storage_service
        logger.info("Gemini TTS initialized successfully")

    # ---------- helpers ----------
    def _pcm16_to_wav(self, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
        """
        Convierte bytes PCM 16-bit a WAV en memoria.
        """
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)  # 2 bytes = 16-bit
            wf.setframerate(rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    # ---------- API pública ----------
    def generate_podcast_audio(
        self,
        text: str,
        *,
        voice_name: str = "Kore",
        gcs_path: str = "retodia/podcasts/podcast.wav",
        channels: int = 1,
        rate: int = 24000,
    ) -> str:
        """
        Genera audio TTS (PCM 16-bit) con Gemini y lo guarda como WAV en GCS.
        Retorna: URI de GCS (o la URL que devuelva tu StorageService).
        """
        if not text or not text.strip():
            raise ValueError("Texto vacío para TTS")

        logger.info("Generating podcast audio with Gemini TTS (voice=%s)", voice_name)

        # Solicita audio al modelo TTS
        resp = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            ),
        )

        # Extrae bytes de audio (PCM 16-bit 24kHz)
        try:
            part = resp.candidates[0].content.parts[0]
        except Exception as e:
            raise RuntimeError(f"No se obtuvo audio de Gemini TTS: {e}")

        # En builds recientes viene como bytes crudos en inline_data.data
        pcm: bytes = getattr(getattr(part, "inline_data", None), "data", None)
        if not isinstance(pcm, (bytes, bytearray)):
            # fallback: si viniera base64/str, aquí podrías decodificar
            raise RuntimeError("Los datos de audio devueltos por TTS no son bytes PCM esperados")

        wav_bytes = self._pcm16_to_wav(pcm, channels=channels, rate=rate)

        # Sube a GCS
        uri = self.storage.upload_bytes(wav_bytes, dest_path=gcs_path, content_type="audio/wav")
        logger.info("Podcast audio uploaded successfully -> %s", uri)
        return uri

    # Método utilitario opcional para clips cortos
    def tts_clip(
        self,
        text: str,
        *,
        voice_name: str = "Kore",
        gcs_path: str = "retodia/tts/clip.wav",
    ) -> str:
        return self.generate_podcast_audio(text, voice_name=voice_name, gcs_path=gcs_path)
