# assistant_core.py
# assistant_core.py
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
import os, json
import asyncio

base_dir = os.path.dirname(os.path.dirname(__file__))  # goes one level up from /src
load_dotenv(os.path.join(base_dir, ".env"))

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=(
"""A knowledgeable and friendly automotive diagnostic assistant that interacts primarily via voice, but can also process images, videos, and text. It supports mechanics in identifying and resolving vehicle issues by combining symptom-based analysis, diagnostic trouble code (DTC) lookup, and internet search when required.
The assistant understands mechanic inputs in natural language, recognizes visual evidence from images and videos, and queries authoritative sources (e.g., Bosch automotive data, internal databases) to generate accurate, actionable repair steps. When information is missing, it intelligently searches the web and compiles the most relevant results.
Core Capabilities
Voice-first interaction – Listen, understand, and converse naturally with mechanics, while supporting text, image, and video inputs for enhanced context.
Symptom & DTC recognition – Detect whether the mechanic is giving a direct trouble code (e.g., P0420) or describing symptoms.
Fault database lookup – Match the DTC or symptoms against internal databases (e.g., Bosch data) to retrieve validated causes and repair steps.
Internet fallback – If no matching data is found, search reputable automotive sources online and summarize findings.
Step-by-step guided repair – Provide one repair step at a time, wait for the mechanic to confirm completion or add input, then proceed to the next step.
Image & video analysis – Use visual inspection to detect signs of wear, damage, or leaks, and match them to known faults.
Context-aware clarification – If mechanic input is incomplete or unclear, ask clarifying questions before giving a diagnosis.
Response Rules
If a valid DTC is provided:
Return:
Error Code Found: [DTC]
Description: [Brief]
Cause: [Known/Likely causes]
Diagnosis Steps: (step-by-step list)
If no match in database:
"I couldn’t find diagnostic information for [DTC]. Would you like me to search the web for possible causes or fixes?"
If only symptoms are provided:
Reformulate symptoms into possible DTC matches.
List probable causes and step-by-step diagnosis.
If no match:
"I couldn’t find any diagnostic information for these symptoms. Would you like me to search online for potential causes?"
If unrelated to automotive:
"I’m here to help with vehicle diagnostics and repair questions. Could you share details about the vehicle issue or error code?"
Tone & Interaction Style
Friendly, professional, and supportive.
Never mention internal tools or databases.
Avoid repeating the user’s question.
No made-up or unverified answers.
Always aim for actionable, clear repair guidance."""
  ))

def _pick_config_from_lang(code: str):
    c = (code or "en").lower()
    if c == "hi":
        import configs.hindi_config as cfg; return cfg
    if c == "kn":
        import configs.kannada_config as cfg; return cfg
    import configs.english_config as cfg; return cfg

#async def entrypoint(ctx: agents.JobContext):
#    await ctx.connect()

    # Default comes from env for console mode; FE metadata overrides in dev mode
#    lang = os.getenv("AGENT_LANG", "en")

    # Try to read participant metadata quickly (frontend sets it after connect)
 #   try:
 #       participant = await ctx.wait_for_participant(timeout=8.0)
 #       if participant and participant.metadata:
 #           md = json.loads(participant.metadata)
 #           lang = (md.get("language") or lang).lower()
 #   except Exception:
 #       pass  # stay with env/default
 #   print(f"[assistant_core] Using language config: {lang}")
 #   cfg = _pick_config_from_lang(lang)

#    session = AgentSession(**cfg.get_config())
#    await session.start(
#        room=ctx.room,
#        agent=Assistant(),
#        room_input_options=RoomInputOptions(video_enabled=True),
#    )

 #   greetings = {
 #       "en": "Hi! I’m your automotive assistant. How can I help today?",
 #       "hi": "नमस्ते! मैं आपका ऑटोमोटिव सहायक हूँ। आज मैं आपकी कैसे मदद कर सकता/सकती हूँ?",
 #       "kn": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ವಾಹನ ಸಹಾಯಕ. ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
 #   }
 #   await session.generate_reply(instructions=greetings.get(lang, greetings["en"]))


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # default if nothing arrives
    lang_box = {"value": os.getenv("AGENT_LANG", "en").lower()}
    got_lang = asyncio.Event()

    # helper to try parse a language from a participant
    def _try_set_lang_from_participant(p):
        try:
            if p and p.metadata:
                md = json.loads(p.metadata)
                sel = (md.get("language") or lang_box["value"]).lower()
                if sel in ("en", "hi", "kn"):
                    if sel != lang_box["value"]:
                        print("[assistant_core] language from token metadata:", sel)
                    lang_box["value"] = sel
                    got_lang.set()
                    return True
        except Exception as e:
            print("[assistant_core] metadata parse error:", e)
        return False

    # 1) If someone is already in the room, check them immediately
    for p in ctx.room.remote_participants.values():
        print("[assistant_core] found existing participant:", getattr(p, "identity", "<unknown>"))
        print("[assistant_core] existing participant.metadata:", p.metadata)
        if _try_set_lang_from_participant(p):
            break

        # also listen for late metadata updates on this participant
        @p.on("metadata_changed")
        def _on_meta_changed():
            print("[assistant_core] participant.metadata_changed:", p.metadata)
            _try_set_lang_from_participant(p)

    # 2) Listen for new participant joins
    @ctx.room.on("participant_connected")
    def _on_participant_connected(p):
        print("[assistant_core] participant_connected:", getattr(p, "identity", "<unknown>"))
        print("[assistant_core] connected participant.metadata:", p.metadata)
        if not _try_set_lang_from_participant(p):
            # watch for later metadata changes
            @p.on("metadata_changed")
            def _on_meta_changed():
                print("[assistant_core] participant.metadata_changed:", p.metadata)
                _try_set_lang_from_participant(p)

    # 3) Data-message fallback (FE sends after connect)
    @ctx.room.on("data_received")
    def _on_data(pkt):
        try:
            if getattr(pkt, "topic", None) == "config":
                payload = json.loads(bytes(pkt.data).decode())
                sel = (payload.get("language") or lang_box["value"]).lower()
                if sel in ("en", "hi", "kn"):
                    if sel != lang_box["value"]:
                        print("[assistant_core] language from data message:", sel)
                    lang_box["value"] = sel
                    got_lang.set()
        except Exception as e:
            print("[assistant_core] data parse error:", e)

    # Wait up to 8s for any of the above to set the language
    try:
        await asyncio.wait_for(got_lang.wait(), timeout=8.0)
    except asyncio.TimeoutError:
        print("[assistant_core] no language override received in time; using default")

    lang = lang_box["value"]
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
                use_separate_process=False,
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
