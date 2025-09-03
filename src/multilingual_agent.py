# src/multilingual_agent.py
import sys, os, multiprocessing
multiprocessing.set_start_method("spawn", force=True)

# Keep plugin registration on the main thread to avoid "Plugins must be registered on the main thread"
# Import ONLY the plugins you actually use in configs.*
from livekit.plugins import openai as _openai  # noqa: F401
from livekit.plugins import cartesia as _cartesia  # noqa: F401
from livekit.plugins import deepgram as _deepgram  # noqa: F401
from livekit.plugins import google as _google  # noqa: F401
from livekit.plugins import silero as _silero  # noqa: F401
from livekit.plugins import sarvam as _sarvam  # noqa: F401
from livekit.plugins.turn_detector import multilingual as _turn_multilingual  # noqa: F401

from assistant_core import run_agent  # run_agent() chooses config based on env/metadata  :contentReference[oaicite:2]{index=2}

LANG_ALIASES = {
    "en": "en", "english": "en",
    "hi": "hi", "hindi": "hi",
    "kn": "kn", "kannada": "kn",
}

VOICEBASE_ALIASES = {
    "voice assistant": "Voice Assistant",
    "live assistant": "Live Assistant",
    "voice": "Voice Assistant",
    "live": "Live Assistant",
}

def usage():
    print(
        "Usage:\n"
        "  python src\\multilingual_agent.py console <lang> [voicebase]\n"
        "    - lang = en|hi|kn|english|hindi|kannada\n"
        "    - voicebase = 'Voice Assistant' | 'Live Assistant'\n"
        "\n"
        "Examples:\n"
        "  python src\\multilingual_agent.py console en\n"
        "  python src\\multilingual_agent.py console hi \"Live Assistant\"\n"
        "  python src\\multilingual_agent.py dev\n"
        "  python src\\multilingual_agent.py download-files [args...]\n"
        "  python src\\multilingual_agent.py <any-livekit-mode> [args...]"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage(); sys.exit(1)

    args_orig  = sys.argv[1:]
    args_lower = [a.lower() for a in args_orig]

    # --- console mode (both orders supported) ---
    if "console" in args_lower:
        idx = args_lower.index("console")

        # discover language candidate near 'console'
        candidates = []
        if len(args_lower) == 2:
            candidates = [args_lower[0] if idx == 1 else args_lower[1]]
        else:
            if idx > 0: candidates.append(args_lower[idx - 1])
            if idx + 1 < len(args_lower): candidates.append(args_lower[idx + 1])

        norm_lang = None
        for c in candidates:
            if c in LANG_ALIASES:
                norm_lang = LANG_ALIASES[c]
                break
        if not norm_lang:
            usage(); sys.exit(1)

        # detect voicebase if given
        norm_voice = "Voice Assistant"  # default
        for a in args_lower:
            if a in VOICEBASE_ALIASES:
                norm_voice = VOICEBASE_ALIASES[a]
                break

        # Set env for assistant_core
        os.environ["AGENT_MODE"] = "console"
        os.environ["AGENT_LANG"] = norm_lang
        os.environ["AGENT_VOICEBASE"] = norm_voice

        # Rebuild argv so LiveKit sees just "console" (+ pass other flags)
        new_args = []
        for a in args_orig:
            al = a.lower()
            if al == "console": continue
            if al in LANG_ALIASES: continue
            if al in VOICEBASE_ALIASES: continue
            new_args.append(a)
        sys.argv = [sys.argv[0], "console", *new_args]

        print(f"[multilingual_agent] console mode → lang={norm_lang}, voiceBase={norm_voice}")
        run_agent()
        sys.exit(0)

    # --- dev / download-files / any other livekit mode (passthrough) ---
    mode = args_lower[0]
    os.environ["AGENT_MODE"] = mode
    sys.argv = [sys.argv[0], *args_orig]
    run_agent()
