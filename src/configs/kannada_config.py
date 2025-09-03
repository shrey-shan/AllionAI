from livekit.plugins import openai, silero, sarvam,google
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import os

def get_config(voice_base: str = "Voice Assistant"):
    if voice_base == "Live Assistant":    
        return dict(
                llm=google.beta.realtime.RealtimeModel(
                model="gemini-2.0-flash-exp",
                voice="Puck",
                temperature=0.5,
                language="kn-IN"))
    else:
        return dict(
        stt=sarvam.STT(model="saarika:v2.5", language="kn-IN"),
        llm=openai.LLM(
            model="gpt-4o-mini",               # 👈 include provider prefix for OpenRouter
       #     base_url="https://openrouter.ai/api/v1", # 👈 force it to hit OpenRouter API
        #    api_key=os.getenv("OPENROUTER_API_KEY"), 
            api_key=os.getenv("OPENAI_API_KEY"), 
        ),
        tts=sarvam.TTS(target_language_code="kn-IN", speaker="abhilash"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        use_tts_aligned_transcript=True,
    )
