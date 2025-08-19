# src/multilingual_agent.py
import sys
import multiprocessing
multiprocessing.set_start_method("spawn", force=True)

from assistant_core import run_agent
import configs.english_config as english
import configs.hindi_config as hindi
import configs.kannada_config as kannada

def get_config(language: str):
    lang = language.lower()
    if lang == "english":
        return english
    if lang == "hindi":
        return hindi
    if lang == "kannada":
        return kannada
    raise ValueError(f"Unsupported language: {language}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python multilingual_agent.py <language> [console]")
        sys.exit(1)

    language = sys.argv[1]
    config = get_config(language)

    # Strip the language before handing remaining args (e.g., 'console') to LiveKit CLI
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    run_agent(config)
