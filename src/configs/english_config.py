# english_config.py
import os, sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from livekit.plugins import openai, cartesia, deepgram, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

def get_config():
    return dict(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(
            model="gpt-4o-mini",
        #    base_url="https://openrouter.ai/api/v1",
        #    api_key=os.getenv("OPENROUTER_API_KEY"),   # <- use OpenRouter key
        api_key=os.getenv("OPENAI_API_KEY"), 
        ),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        use_tts_aligned_transcript=True,
    )
