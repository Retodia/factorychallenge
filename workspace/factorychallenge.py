from services.tts_service_gemini import GeminiTTSService

script = """Tone: Warm, conversational.
Speaker 1: Hola, esta es una prueba corta de voz.
Speaker 2: Confirmado. Si escuchas esto, el TTS funciona."""
svc = GeminiTTSService()
audio = svc.generate_podcast_audio(script, user_id="dev", voices={"Speaker 1":"Zephyr","Speaker 2":"Puck"})
open("test.wav","wb").write(audio if audio else b"")
print("Listo -> test.wav" if audio else "Falló la generación")
