## importing LiveKit Agent module and plugins

import logging

from dotenv import load_dotenv
_=load_dotenv(override=True)  ##This line loads environment variables from a .env file, overwriting any existing ones, and ignores the return value.

logger = logging.getLogger('dlai-agent')
logger.setLevel(logging.INFO)

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, jupyter
from livekit.plugins import(
    openai,
    elevenlabs,
    silero,
)

##Defining custom agent

class Assistant(Agent):
    def __init__(self) -> None:
        llm = openai.LLM(model="gpt-4")
        stt = openai.STT()
        ##tts = elevenlabs.TTS()
        tts = elevenlabs.TTS(voice_id="CwhRBWXzGAHq8TQ4Fs17") ##to use specific voice id
        silero_vad = silero.VAD.load()

        super().__init__(
            instructions="""
            You are a helpful assistant communicating via voice
            """,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero_vad,
        )

##entry point:

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant()
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))