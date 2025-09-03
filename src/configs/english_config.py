# english_config.py
import os, sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from livekit.plugins import openai, cartesia, deepgram, silero, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel

def get_config(voice_base: str = "Voice Assistant"):
    if voice_base == "Live Assistant":
        # Use Gemini for Live Assistant
        return dict(
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-2.0-flash-exp",
                voice="Puck",
                temperature=0.5,
            ),
            stt=deepgram.STT(model="nova-3", language="multi"),
            tts=cartesia.TTS(
                model="sonic-2",
                voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",
            ),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
            use_tts_aligned_transcript=True,
        )
    else:
        # Default = Voice Assistant (OpenAI LLM)
        return dict(
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=openai.LLM(
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
            ),
            tts=cartesia.TTS(
                model="sonic-2",
                voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",
            ),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
            use_tts_aligned_transcript=True,
        )
