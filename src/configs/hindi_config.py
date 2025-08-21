from livekit.plugins import openai, silero, sarvam
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import os

def get_config():
    return dict(
        stt=sarvam.STT(model="saarika:v2.5", language="hi-IN"),
        llm=openai.LLM(
            model="gpt-4o-mini",   # 👈 note the "openai/" prefix (OpenRouter convention)
          #  base_url="https://openrouter.ai/api/v1",  # 👈 route through OpenRouter
          #  api_key=os.getenv("OPENROUTER_API_KEY"), 
            api_key=os.getenv("OPENAI_API_KEY"), 
        ),
        tts=sarvam.TTS(target_language_code="hi-IN", speaker="abhilash"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        use_tts_aligned_transcript=True,
    )
