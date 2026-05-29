from pathlib import Path

CONTEXT_DIR = Path('__file__').parent / "contexts"

CONTEXT_FILES = {
    "football": CONTEXT_DIR/ "football.txt",
    "ai": CONTEXT_DIR/ "ai.txt"
}

def load_context(context_type: str) -> str:
    path = CONTEXT_FILES.get(context_type)

    if not path:
        return ""

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8").strip()