# src/multilingual_agent.py
import sys, os, multiprocessing
multiprocessing.set_start_method("spawn", force=True)

# Keep plugin registration on the main thread to avoid "Plugins must be registered on the main thread"
# Import ONLY the plugins you actually use in configs.*
from livekit.plugins import openai as _openai  # noqa: F401
from livekit.plugins import cartesia as _cartesia  # noqa: F401
from livekit.plugins import deepgram as _deepgram  # noqa: F401
from livekit.plugins import silero as _silero  # noqa: F401
from livekit.plugins import sarvam as _sarvam  # noqa: F401
from livekit.plugins.turn_detector import multilingual as _turn_multilingual  # noqa: F401

from assistant_core import run_agent  # run_agent() chooses config based on env/metadata  :contentReference[oaicite:2]{index=2}

LANG_ALIASES = {
  "en": "en", "english": "en",
  "hi": "hi", "hindi": "hi",
  "kn": "kn", "kannada": "kn",
}

def usage():
    print(
        "Usage:\n"
        "  python src\\multilingual_agent.py console <en|hi|kn | english|hindi|kannada>\n"
        "  python src\\multilingual_agent.py <en|hi|kn | english|hindi|kannada> console  # alternate order\n"
        "  python src\\multilingual_agent.py dev\n"
        "  python src\\multilingual_agent.py download-files [args...]  # passthrough\n"
        "  python src\\multilingual_agent.py <any-livekit-mode> [args...]  # passthrough"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage(); sys.exit(1)

    args_orig  = sys.argv[1:]
    args_lower = [a.lower() for a in args_orig]

    # --- console mode (both orders supported) ---
    if "console" in args_lower:
        idx = args_lower.index("console")
        # discover the language token near 'console'
        candidates = []
        if len(args_lower) == 2:
            candidates = [args_lower[0] if idx == 1 else args_lower[1]]
        else:
            if idx > 0: candidates.append(args_lower[idx - 1])
            if idx + 1 < len(args_lower): candidates.append(args_lower[idx + 1])

        norm_lang = None
        for c in candidates:
            if c in LANG_ALIASES:
                norm_lang = LANG_ALIASES[c]; break
        if not norm_lang:
            usage(); sys.exit(1)

        # Set env for assistant_core; it will pick cfg via _pick_config_from_lang
        os.environ["AGENT_MODE"] = "console"
        os.environ["AGENT_LANG"] = norm_lang

        # Rebuild argv so LiveKit sees just "console" (+ pass other non-lang flags through)
        new_args = []
        for a in args_orig:
            al = a.lower()
            if al == "console": continue  # will insert once
            if al in LANG_ALIASES: continue
            new_args.append(a)
        sys.argv = [sys.argv[0], "console", *new_args]
        run_agent()
        sys.exit(0)

    # --- dev / download-files / any other livekit mode (passthrough) ---
    mode = args_lower[0]
    os.environ["AGENT_MODE"] = mode
    # In dev, language comes from frontend metadata; in others we just pass through
    sys.argv = [sys.argv[0], *args_orig]
    run_agent()
