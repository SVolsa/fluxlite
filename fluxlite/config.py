import os
import base64
import hashlib
from pathlib import Path

import tomli_w

try:
    import tomllib
except ImportError:
    import tomli as tomllib

CONFIG_DIR = Path.home() / ".fluxlite"
CONFIG_PATH = CONFIG_DIR / "config.toml"
KEY_FILE = CONFIG_DIR / ".fluxkey"

DEFAULT_CONFIG = {
    "api": {
        "key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "tavily": {
        "key": "",
    },
    "app": {
        "language": "zh",
        "max_turns": 100,
        "safe_mode": True,
        "timeout": 60,
    },
    "tools": {
        "search_enabled": True,
        "code_enabled": True,
        "file_enabled": True,
    },
}


def _get_machine_key() -> bytes:
    raw = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "fluxlite-default"
    return hashlib.sha256(raw.encode()).digest()


def _ensure_fernet():
    try:
        from cryptography.fernet import Fernet
        return Fernet
    except ImportError:
        return None


def _protect_key_file():
    path = str(KEY_FILE)
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        if user:
            import subprocess
            subprocess.run(
                ["icacls", path, "/inheritance:r", "/grant", f"{user}:F"],
                capture_output=True,
            )
    else:
        KEY_FILE.chmod(0o600)


def _load_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = _get_machine_key()
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(key)
    _protect_key_file()
    return key


def _fernet():
    from cryptography.fernet import Fernet as F
    key = base64.urlsafe_b64encode(_load_or_create_key()[:32])
    return F(key)


def encrypt_value(plain: str) -> str:
    if not plain:
        return ""
    if _ensure_fernet():
        try:
            return _fernet().encrypt(plain.encode()).decode()
        except Exception:
            pass
    return plain


def decrypt_value(encrypted: str) -> str:
    if not encrypted:
        return ""
    if _ensure_fernet():
        try:
            return _fernet().decrypt(encrypted.encode()).decode()
        except Exception:
            pass
    return encrypted


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        cfg = dict(tomllib.load(f))
    # Decrypt keys on load
    api_key = cfg.get("api", {}).get("key", "")
    if api_key and not api_key.startswith("sk-"):
        cfg.setdefault("api", {})["key"] = decrypt_value(api_key)
    tavily_key = cfg.get("tavily", {}).get("key", "")
    if tavily_key and not tavily_key.startswith("tvly-"):
        cfg.setdefault("tavily", {})["key"] = decrypt_value(tavily_key)
    return cfg


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {}
    for section, values in config.items():
        cfg[section] = dict(values)
    # Encrypt keys on save
    api_key = cfg.get("api", {}).get("key", "")
    if api_key:
        cfg["api"]["key"] = encrypt_value(api_key)
    tavily_key = cfg.get("tavily", {}).get("key", "")
    if tavily_key:
        cfg["tavily"]["key"] = encrypt_value(tavily_key)
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(cfg, f)


def is_configured() -> bool:
    cfg = load_config()
    key = cfg.get("api", {}).get("key", "")
    return bool(key)


def get(key: str, default=None):
    cfg = load_config()
    parts = key.split(".")
    val = cfg
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return default
    return val if val is not None else default
