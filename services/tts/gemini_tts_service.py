# services/tts/gemini_tts_service.py
import os
import io
import mimetypes
import struct
from typing import Dict, Optional
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-pro-preview-tts"

class GeminiTTSService:
    """
    Servicio TTS con Gemini (multi-speaker).
    Usa etiquetas de texto como:
      Speaker 1: Hola...
      Speaker 2: Responde...
    y mapea cada speaker a una voz.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        # Usa API key desde argumento o desde env var GEMINI_API_KEY
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("Falta GEMINI_API_KEY para inicializar GeminiTTSService")

        self.client = genai.Client(api_key=key)
        self.model = model

    def _convert_pcm_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        params = self._parse_audio_mime(mime_type)
        bits_per_sample = params["bits_per_sample"] or 16
        sample_rate = params["rate"] or 24000
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", chunk_size, b"WAVE",
            b"fmt ", 16, 1,
            num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
            b"data", data_size
        )
        return header + audio_data

    def _parse_audio_mime(self, mime_type: str):
        bits_per_sample = 16
        rate = 24000
        for part in (mime_type or "").split(";"):
            p = part.strip().lower()
            if p.startswith("rate="):
                try:
                    rate = int(p.split("=", 1)[1])
                except Exception:
                    pass
            if p.startswith("audio/l"):
                try:
                    bits_per_sample = int(p.split("l", 1)[1])
                except Exception:
                    pass
        return {"bits_per_sample": bits_per_sample, "rate": rate}

    def _make_contents(self, script_text: str) -> list[types.Content]:
        return [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=script_text)]
            )
        ]

    def _make_config(self, speakers_to_voices: Dict[str, str], temperature: float = 1.2):
        ms_config = types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[
                types.SpeakerVoiceConfig(
                    speaker=speaker_label,
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    ),
                )
                for speaker_label, voice_name in speakers_to_voices.items()
            ]
        )
        return types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=ms_config
            ),
        )

    def synthesize_dialog(
        self,
        script_text: str,
        speakers_to_voices: Dict[str, str],
        out_basename: str = "dialogo"
    ) -> str:
        contents = self._make_contents(script_text)
        cfg = self._make_config(speakers_to_voices)

        audio_chunks: list[bytes] = []
        final_mime: Optional[str] = None

        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=cfg,
        ):
            if not chunk.candidates or not chunk.candidates[0].content:
                continue
            parts = chunk.candidates[0].content.parts or []
            if not parts:
                continue
            part0 = parts[0]
            if getattr(part0, "inline_data", None) and part0.inline_data.data:
                final_mime = part0.inline_data.mime_type or final_mime
                audio_chunks.append(part0.inline_data.data)

        if not audio_chunks:
            raise RuntimeError("No se recibieron datos de audio del stream.")

        audio_bytes = b"".join(audio_chunks)

        ext = mimetypes.guess_extension(final_mime or "")
        if ext is None:
            ext = ".wav"
            audio_bytes = self._convert_pcm_to_wav(audio_bytes, final_mime or "audio/L16;rate=24000")

        out_path = f"{out_basename}{ext}"
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        return out_path
