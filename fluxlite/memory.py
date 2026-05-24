"""Dynamic memories — knowledge learned during conversation (~/.fluxlite/memory.json)."""
import json
from pathlib import Path
from datetime import datetime

MEMORY_PATH = Path.home() / ".fluxlite" / "memory.json"


def load_memories() -> list:
    if MEMORY_PATH.exists():
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("memories", [])
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, IOError, OSError):
            pass
    return []


def save_memories(entries: list):
    try:
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_PATH.write_text(
            json.dumps({"memories": entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, PermissionError, TypeError):
        pass


def add_memory(content: str) -> dict:
    entry = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    entries = load_memories()
    entries.append(entry)
    save_memories(entries)
    return entry
