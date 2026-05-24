"""Identity and rules — persistent profile (~/.fluxlite/profile.json)."""
import json
import copy
from pathlib import Path
from datetime import datetime

PROFILE_PATH = Path.home() / ".fluxlite" / "profile.json"
_OLD_MEMORY_PATH = Path.home() / ".fluxlite" / "memory.json"

DEFAULT_PROFILE = {
    "identity": {
        "name": "",
        "personality": "",
        "user_name": "",
        "created_at": "",
    },
    "rules": [],
}


def _migrate_old() -> dict | None:
    if not _OLD_MEMORY_PATH.exists():
        return None
    if PROFILE_PATH.exists():
        return None
    try:
        old = json.loads(_OLD_MEMORY_PATH.read_text(encoding="utf-8"))
        identity = old.get("identity", {})
        rules = old.get("rules", [])
        if identity.get("name") or rules:
            profile = {"identity": identity, "rules": rules}
            PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            PROFILE_PATH.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            old.pop("identity", None)
            old.pop("rules", None)
            remaining = {k: old[k] for k in old if old[k]}
            if remaining.get("memories"):
                _OLD_MEMORY_PATH.write_text(
                    json.dumps(remaining, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                _OLD_MEMORY_PATH.unlink(missing_ok=True)
            return profile
    except (json.JSONDecodeError, OSError, PermissionError, TypeError):
        pass
    return None


def load_profile() -> dict:
    migrated = _migrate_old()
    if migrated:
        return migrated

    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            if "identity" in data:
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return copy.deepcopy(DEFAULT_PROFILE)


def save_profile(profile: dict):
    try:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, PermissionError, TypeError):
        pass


def add_rule(profile: dict, rule: str):
    profile.setdefault("rules", []).append(rule)
    save_profile(profile)


def remove_rule(profile: dict, index: int) -> bool:
    rules = profile.get("rules", [])
    if 0 <= index < len(rules):
        rules.pop(index)
        save_profile(profile)
        return True
    return False
