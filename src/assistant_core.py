# assistant_core.py
# assistant_core.py (only the entrypoint function shown)
import asyncio  # make sure this import exists at top
import json
import os
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Default lang; frontend metadata can override in dev
    lang = os.getenv("AGENT_LANG", "en").lower()

    participant = None
    try:
        # ⬅️ Correct: wrap with asyncio.wait_for (NOT ctx.wait_for)
        participant = await asyncio.wait_for(ctx.wait_for_participant(), timeout=8.0)
    except asyncio.TimeoutError:
        print("[assistant_core] wait_for_participant timed out")
        # fallback: pick first remote participant if any
        participant = next(iter(ctx.room.remote_participants.values()), None)
    except Exception as e:
        print("[assistant_core] wait_for_participant error:", e)

    # Poll briefly for FE post-connect setMetadata()
    if participant:
        print("[assistant_core] joined participant:", getattr(participant, "identity", "<unknown>"))
        print("[assistant_core] participant.metadata (initial):", participant.metadata)
        for _ in range(16):  # ~8s total (16 * 0.5s)
            md_str = participant.metadata
            if not md_str:
                await asyncio.sleep(0.5)
                continue
            try:
                md = json.loads(md_str)
                selected = (md.get("language") or lang).lower()
                if selected in ("en", "hi", "kn"):
                    lang = selected
            except Exception as e:
                print("[assistant_core] metadata parse error:", e)
            break

    print(f"[assistant_core] Using language config: {lang}")

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
