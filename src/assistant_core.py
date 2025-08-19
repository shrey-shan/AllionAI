from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions

load_dotenv()

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=(
            "Friendly automotive assistant for mechanics. "
            "Understands voice, images, text, and video to identify faults via DTCs or symptoms. "
            "Uses trusted data, web search if needed, and guides repair step-by-step, confirming after each step. "
            "If unrelated to automotive: I’m here to help with vehicle diagnostics and repair questions. "
            "Could you share details about the vehicle issue or error code?"
        ))

async def entrypoint(ctx: agents.JobContext, config_module):
    await ctx.connect()
    session = AgentSession(**config_module.get_config())
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(video_enabled=True),
    )
    await session.generate_reply(instructions="Greet the user and offer your assistance.")

def run_agent(config_module):
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=lambda ctx: entrypoint(ctx, config_module),
            initialize_process_timeout=60.0,
            shutdown_process_timeout=60.0,
            job_memory_warn_mb=15000,
        )
    )
