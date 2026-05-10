import json
from pathlib import Path
from datetime import datetime

MEMORY_PATH = Path.home() / ".fluxlite" / "memory.json"

DEFAULT_MEMORY = {
    "identity": {
        "name": "",
        "personality": "",
        "user_name": "",
        "created_at": "",
    },
    "memories": [],
    "rules": [],
}


def load_memory() -> dict:
    if MEMORY_PATH.exists():
        try:
            with open(MEMORY_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if "identity" in data:
                return data
        except (json.JSONDecodeError, IOError):
            pass
    import copy
    return copy.deepcopy(DEFAULT_MEMORY)


def save_memory(memory: dict):
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def add_memory(memory: dict, content: str):
    entry = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    memory["memories"].append(entry)
    save_memory(memory)


def add_rule(memory: dict, rule: str):
    memory["rules"].append(rule)
    save_memory(memory)


def remove_rule(memory: dict, index: int) -> bool:
    if 0 <= index < len(memory["rules"]):
        memory["rules"].pop(index)
        save_memory(memory)
        return True
    return False
