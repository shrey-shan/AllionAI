from livekit.plugins import openai, silero, sarvam
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import os

def get_config():
    return dict(
        stt=sarvam.STT(model="saarika:v2.5", language="kn-IN"),
        llm=openai.LLM(
            model="gpt-4o",               # 👈 include provider prefix for OpenRouter
       #     base_url="https://openrouter.ai/api/v1", # 👈 force it to hit OpenRouter API
        #    api_key=os.getenv("OPENROUTER_API_KEY"), 
            api_key=os.getenv("OPENAI_API_KEY"), 
        ),
        tts=sarvam.TTS(target_language_code="kn-IN", speaker="abhilash"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        use_tts_aligned_transcript=True,
    )
