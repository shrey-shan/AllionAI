# assistant_core.py
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
import os

base_dir = os.path.dirname(os.path.dirname(__file__))  # goes one level up from /src
load_dotenv(os.path.join(base_dir, ".env"))

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
    # Prefer single process on Windows to avoid IPC crashes
    # Try the explicit option if available; otherwise fall back to env toggle.
    try:
        agents.cli.run_app(
            agents.WorkerOptions(
                entrypoint_fnc=lambda ctx: entrypoint(ctx, config_module),
                initialize_process_timeout=60.0,
                shutdown_process_timeout=60.0,
                job_memory_warn_mb=15000,
                # 👇 key line: keep everything in one process
                use_separate_process=False,
            )
        )
    except TypeError:
        # Older versions may not have `use_separate_process`. Use env flag instead.
        os.environ["LIVEKIT_AGENTS_DISABLE_SEPARATE_PROCESS"] = "1"
        agents.cli.run_app(
            agents.WorkerOptions(
                entrypoint_fnc=lambda ctx: entrypoint(ctx, config_module),
                initialize_process_timeout=60.0,
                shutdown_process_timeout=60.0,
                job_memory_warn_mb=15000,
            )
        )
