from dotenv import load_dotenv
import os

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="Friendly automotive assistant for mechanics. Understands voice, images, text, and video to identify faults via DTCs or symptoms. Uses trusted data, web search if needed, and guides repair step-by-step, confirming after each step.If unrelated to automotive: I’m here to help with vehicle diagnostics and repair questions. Could you share details about the vehicle issue or error code?")


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini", base_url=os.getenv("OPENAI_API_BASE"),),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),use_tts_aligned_transcript=True,
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(video_enabled=True,
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint,initialize_process_timeout=60.0,     # bump to 60 s
            shutdown_process_timeout=60.0,       # optional: shorten shutdown if desired
            job_memory_warn_mb=15000,))


