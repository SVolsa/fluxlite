"""Plugin manager — discover, load, and manage FluxLite plugins.

Plugin structure (~/.fluxlite/plugins/<name>/):
  <name>.json   — metadata + tool schema definitions
  <name>.py     — handler functions (one per tool)
"""

import os
import json
import shutil
import threading
import importlib.util
from pathlib import Path
from dataclasses import dataclass


PLUGINS_DIR = Path.home() / ".fluxlite" / "plugins"
_STATE_FILE = Path.home() / ".fluxlite" / "plugin_state.json"

_lock = threading.Lock()
_plugins: dict[str, dict] = {}
_state: dict[str, bool] = {}


@dataclass
class PluginToolDef:
    name: str
    description: str
    parameters: dict
    handler: callable


def _load_state():
    global _state
    try:
        if _STATE_FILE.exists():
            _state = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        _state = {}


def _save_state():
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def discover():
    global _plugins
    _load_state()

    plugins = {}
    if not PLUGINS_DIR.is_dir():
        _plugins = plugins
        return

    for folder in sorted(PLUGINS_DIR.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        info = _load_single_plugin(folder)
        if info:
            plugins[folder.name] = info

    _plugins = plugins


def _load_single_plugin(folder: Path) -> dict | None:
    name = folder.name
    json_path = folder / f"{name}.json"
    py_path = folder / f"{name}.py"

    if not json_path.exists():
        return None

    try:
        meta = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _error_plugin(name, f"Invalid JSON: {e}")
    except Exception as e:
        return _error_plugin(name, str(e))

    if not isinstance(meta, dict):
        return _error_plugin(name, "JSON root must be an object")
    if not meta.get("tools"):
        return _error_plugin(name, "No tools defined in JSON")

    if not py_path.exists():
        return _error_plugin(name, f"Missing {name}.py")

    module = _import_module(name, py_path)
    if module is None:
        return _error_plugin(name, f"Failed to import {name}.py")

    tools = []
    for tdef in meta["tools"]:
        if not isinstance(tdef, dict) or not tdef.get("name"):
            continue
        func_name = tdef["name"]
        handler = getattr(module, func_name, None)
        if handler is None:
            tools.append(_error_tool(func_name, f"Handler '{func_name}' not found in {name}.py"))
            continue
        if not callable(handler):
            tools.append(_error_tool(func_name, f"'{func_name}' is not callable"))
            continue

        tools.append(PluginToolDef(
            name=f"plugin_{name}_{func_name}",
            description=f"[{name}] {tdef.get('description', '')}",
            parameters=tdef.get("parameters", {}),
            handler=_wrap_handler(name, func_name, handler),
        ))

    enabled = _state.get(name, True)
    return {
        "name": name,
        "meta": meta,
        "module": module,
        "tools": tools,
        "enabled": enabled,
        "error": None,
    }


def _import_module(name: str, py_path: Path):
    try:
        spec = importlib.util.spec_from_file_location(f"__plugins__.{name}", py_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _wrap_handler(plugin_name: str, func_name: str, handler: callable):
    def _wrapped(**kwargs):
        try:
            return handler(kwargs)
        except Exception as e:
            return f"[Plugin {plugin_name}] Error in {func_name}: {e}"
    _wrapped.__name__ = func_name
    return _wrapped


def _error_plugin(name: str, error: str) -> dict:
    return {
        "name": name,
        "meta": {"name": name, "version": "?", "description": f"[load error]" },
        "module": None,
        "tools": [],
        "enabled": False,
        "error": error,
    }


def _error_tool(name: str, error: str) -> PluginToolDef:
    return PluginToolDef(
        name=f"plugin_error_{name}",
        description=f"[BROKEN] {error}",
        parameters={},
        handler=lambda args: f"[Plugin Error] {error}",
    )


def get_plugin_tools() -> list[PluginToolDef]:
    with _lock:
        tools = []
        for name, info in _plugins.items():
            if not info.get("enabled"):
                continue
            tools.extend(info.get("tools", []))
        return tools


def get_tool_schemas() -> list[dict]:
    schemas = []
    for tool in get_plugin_tools():
        schemas.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": dict(tool.parameters),
        })
    return schemas


def list_plugins() -> str:
    with _lock:
        if not _plugins:
            return "No plugins found in ~/.fluxlite/plugins/"

        lines = [f"Plugins ({len(_plugins)}):"]
        for name, info in _plugins.items():
            meta = info.get("meta", {})
            ver = meta.get("version", "?")
            desc = meta.get("description", "")
            err = info.get("error")
            enabled = info.get("enabled", False)
            status = "enabled" if enabled else "disabled"
            if err:
                status = "error"
            tool_count = len(info.get("tools", []))
            lines.append(f"  [{status}] {name} v{ver} — {desc} ({tool_count} tools)")
            if err:
                lines.append(f"    Error: {err}")
        return "\n".join(lines)


def plugin_info(name: str) -> str:
    with _lock:
        info = _plugins.get(name)
        if not info:
            return f"Plugin '{name}' not found"

        meta = info.get("meta", {})
        lines = [
            f"Name: {meta.get('name', name)}",
            f"Version: {meta.get('version', '?')}",
            f"Author: {meta.get('author', '?')}",
            f"Website: {meta.get('website', '')}",
            f"Description: {meta.get('description', '')}",
            f"Enabled: {info.get('enabled', False)}",
        ]
        err = info.get("error")
        if err:
            lines.append(f"Error: {err}")
        lines.append("")
        lines.append("Tools:")
        for tool in info.get("tools", []):
            params = ", ".join(tool.parameters.keys()) if tool.parameters else "(no params)"
            lines.append(f"  {tool.name}({params}) — {tool.description}")
        return "\n".join(lines)


def enable_plugin(name: str) -> str:
    with _lock:
        if name not in _plugins:
            return f"Plugin '{name}' not found"
        if _plugins[name].get("error"):
            return f"Plugin '{name}' has errors and cannot be enabled: {_plugins[name]['error']}"
        _plugins[name]["enabled"] = True
        _state[name] = True
        _save_state()
        return f"Plugin '{name}' enabled"


def disable_plugin(name: str) -> str:
    with _lock:
        if name not in _plugins:
            return f"Plugin '{name}' not found"
        _plugins[name]["enabled"] = False
        _state[name] = False
        _save_state()
        return f"Plugin '{name}' disabled"


def reload_plugins():
    with _lock:
        discover()
    return "Plugins reloaded"


def create_plugin(name: str) -> str:
    plugin_dir = PLUGINS_DIR / name
    if plugin_dir.exists():
        return f"Plugin '{name}' already exists at {plugin_dir}"

    plugin_dir.mkdir(parents=True, exist_ok=True)

    json_content = {
        "name": name,
        "version": "1.0.0",
        "description": "Describe your plugin here",
        "author": "Your Name",
        "website": "",
        "tools": [
            {
                "name": "hello",
                "description": "Example tool — says hello",
                "parameters": {
                    "name": {"type": "string", "desc": "Name to greet", "optional": True}
                }
            }
        ]
    }
    (plugin_dir / f"{name}.json").write_text(
        json.dumps(json_content, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    py_content = f'''"""\"{name} plugin — FluxLite"""
from fluxlite.plugin_api import PluginError, format_result


def hello(args: dict) -> str:
    """\"Say hello to someone."""
    name = args.get("name", "World")
    return format_result({{"message": f"Hello, {{name}}!"}})
'''
    (plugin_dir / f"{name}.py").write_text(py_content, encoding="utf-8")

    return f"Plugin '{name}' scaffolded at {plugin_dir}"
