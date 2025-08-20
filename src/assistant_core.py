# assistant_core.py
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
import os, json

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

def _pick_config_from_lang(code: str):
    c = (code or "en").lower()
    if c == "hi":
        import configs.hindi_config as cfg; return cfg
    if c == "kn":
        import configs.kannada_config as cfg; return cfg
    import configs.english_config as cfg; return cfg

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Default comes from env for console mode; FE metadata overrides in dev mode
    lang = os.getenv("AGENT_LANG", "en").lower()

    # Try to read participant metadata quickly (frontend sets it after connect)
    try:
    # Wait for the first participant to join
        participant = await ctx.wait_for_participant(timeout=8.0)
    # Poll a few times for metadata because FE may call setMetadata() right after connect
        if participant:
            for _ in range(16):  # ~8s total (16 * 0.5s)
                if participant.metadata:
                    md = json.loads(participant.metadata)
                    selected = (md.get("language") or lang).lower()
                    if selected in ("en", "hi", "kn"):
                        lang = selected
                    break
                await asyncio.sleep(0.5)
    except Exception:
        pass  # keep env/default "en"

    cfg = _pick_config_from_lang(lang)

    session = AgentSession(**cfg.get_config())
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(video_enabled=True),
    )

    greetings = {
        "en": "Hi! I’m your automotive assistant. How can I help today?",
        "hi": "नमस्ते! मैं आपका ऑटोमोटिव सहायक हूँ। आज मैं आपकी कैसे मदद कर सकता/सकती हूँ?",
        "kn": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ವಾಹನ ಸಹಾಯಕ. ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
    }
    await session.generate_reply(instructions=greetings.get(lang, greetings["en"]))

def run_agent():
    # Single-process avoids Windows IPC issues
    try:
        agents.cli.run_app(
            agents.WorkerOptions(
                entrypoint_fnc=entrypoint,
                initialize_process_timeout=60.0,
                shutdown_process_timeout=60.0,
                job_memory_warn_mb=15000,
               
            )
        )
    except TypeError:
        os.environ["LIVEKIT_AGENTS_DISABLE_SEPARATE_PROCESS"] = "1"
        agents.cli.run_app(
            agents.WorkerOptions(
                entrypoint_fnc=entrypoint,
                initialize_process_timeout=60.0,
                shutdown_process_timeout=60.0,
                job_memory_warn_mb=15000,
            )
        )
