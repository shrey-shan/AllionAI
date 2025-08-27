# assistant_core.py
# assistant_core.py
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
import os, json
import asyncio
from .vision_capabilities import VisionCapabilities
from .rag_capabilities import RepairAssistantStateMachine
from .configs.rag_config import RAGConfig
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

base_dir = os.path.dirname(os.path.dirname(__file__))  # goes one level up from /src
load_dotenv(os.path.join(base_dir, ".env"))

class Assistant(VisionCapabilities,Agent):
    def __init__(self) -> None:
        Agent.__init__(self,instructions=(
            """You are Allion, a knowledgeable and friendly automotive diagnostic assistant that interacts primarily via voice. You help mechanics identify and resolve vehicle issues by combining symptom analysis, DTC lookup, and diagnostic guidance.

CORE CAPABILITIES:
- Voice-first natural conversation with mechanics
- DTC recognition and symptom-based analysis  
- Step-by-step guided diagnostics (one step at a time)
- Image and video analysis for visual inspection
- Context-aware clarification when input is unclear

CRITICAL SPEAKING RULES:
- Speak naturally in complete sentences, NEVER use bullet points, asterisks (*), dashes (-), or numbered lists
- Provide ONE diagnostic step at a time, then wait for mechanic feedback
- Ask clarifying questions before giving diagnosis if input is unclear
- Use conversational mechanic language: "Let's check...", "I'd start with...", "That tells me..."
- Sound like an experienced shop colleague, not a manual

DIAGNOSTIC APPROACH:
You have access to two tools: `search_documents` and `search_web`.
ALWAYS prioritize `search_documents` first to check your internal knowledge base of PDFs.
ONLY use `search_web` if `search_documents` returns no relevant information or indicates that local search is unavailable.

When given a DTC code (e.g., P0420):
- State: "I found error code P0420, which indicates [brief description]"  
- Explain: "The most common cause is [primary cause]"
- Guide: "Let's start by checking [first step]. Can you [specific action]?"

When given symptoms only:
- Ask clarifying questions: "Tell me, does this happen when cold, warm, or both?"
- Suggest most likely cause: "Based on those symptoms, I'm thinking [specific issue]"
- Guide: "Let's test that theory. First, can you [specific diagnostic step]?"

When no database match found:
- Say: "I don't have specific diagnostic data for this issue. Let me search online for the most current repair procedures."
- After searching: "Here's what I found from reputable sources..."

CONVERSATION FLOW:
1. Listen to mechanic's description
2. Use your tools (`search_documents` first, then `search_web`) to find information.
3. Suggest the MOST LIKELY cause (not multiple options)
4. Guide through ONE specific test or check
5. Wait for their results before suggesting next step
6. Continue step-by-step until problem is resolved

EXAMPLE GOOD RESPONSE:
Mechanic: "I've got code P0171 on a 2019 Ford F-150"
You: "P0171 means your engine is running too lean on bank one. The most common cause on F-150s is a dirty mass airflow sensor. When did you last replace the air filter? Let's start by checking the MAF sensor for contamination."

EXAMPLE BAD RESPONSE (NEVER DO THIS):
"P0171 causes include:
* Dirty MAF sensor
* Vacuum leak  
* Bad fuel pump
* Clogged fuel filter"

IMAGE/VIDEO ANALYSIS:
When shown visual evidence:
- Identify what you see: "I can see the brake rotor there"
- Comment on condition: "That rotor shows significant scoring"
- Connect to problem: "This explains the grinding noise you mentioned"
- Next step: "Let's measure the rotor thickness to see if it's within spec"

SAFETY REMINDERS:
Integrate safety naturally:
- "Make sure the engine is cool first"
- "Use jack stands for this one" 
- "Safety glasses recommended"

WHEN INFORMATION IS MISSING:
- For unknown DTCs: "I need to search for current diagnostic info on this code. Let me find the latest repair procedures."
- For unclear symptoms: Ask specific questions to narrow down the issue
- For non-automotive queries: "I specialize in vehicle diagnostics. What specific car problem can I help you with?"

TONE: Friendly, professional, supportive. Sound like a knowledgeable mechanic colleague who's there to help solve the problem together.

Remember: You're having a conversation, not reading a checklist. Guide mechanics through logical diagnostic steps one at a time, building on their feedback to reach the solution."""
        ))
        VisionCapabilities.__init__(self)
        # Initialize RAG Manager
        self.rag_config = RAGConfig()
        self.rag_enabled = getattr(self.rag_config, 'RAG_ENABLED', True)
        
        if self.rag_enabled:
            # Use the fixed RepairAssistantStateMachine as your RAG manager
            self.rag_manager = RepairAssistantStateMachine(self.rag_config)
            logger.info("RAG Manager initialized successfully")
        else:
            self.rag_manager = None
            logger.info("RAG disabled in configuration")

    @property
    def tools(self):
        """Expose RAG tools to the LLM."""
        if self.rag_enabled and self.rag_manager:
            return self.rag_manager.available_tools
        return []

    async def get_system_status(self) -> dict:
        """Return system-level status for debugging and integration testing."""
        rag_health = {"status": "disabled", "initialized": False}
        
        if self.rag_enabled and self.rag_manager:
            # The RAG manager now has get_health() method directly
            rag_health = self.rag_manager.get_health()
        
        status = {
            "status": "ok",
            "assistant_ready": True,
            "rag_enabled": self.rag_enabled,
            "rag_health": rag_health,
            "rag_initialized": rag_health.get("initialized", False),
        }
        return status

def _pick_config_from_lang(code: str):
    c = (code or "en").lower()
    if c == "hi":
        from .configs import hindi_config as cfg; return cfg
    if c == "kn":
        from .configs import kannada_config as cfg; return cfg
    from .configs import english_config as cfg; return cfg

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

    # For console mode, language is passed directly via env var.
    # For dev mode, we need to detect it from participant metadata.
    mode = os.getenv("AGENT_MODE", "dev")

    if mode == "console":
        lang = os.getenv("AGENT_LANG", "en").lower()
    else:  # dev mode
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