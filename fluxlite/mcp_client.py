"""MCP (Model Context Protocol) client for FluxLite.

Connects to MCP servers via stdio JSON-RPC transport.
Server config: ~/.fluxlite/mcp.json
"""
import json
import subprocess
import sys
from pathlib import Path

MCP_CONFIG = Path.home() / ".fluxlite" / "mcp.json"

_servers: dict[str, dict] = {}
_initialized = False


def load_config() -> list[dict]:
    if not MCP_CONFIG.exists():
        return []
    try:
        data = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
        return data.get("servers", [])
    except (json.JSONDecodeError, OSError, PermissionError):
        return []


def save_config(servers: list[dict]):
    try:
        MCP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        MCP_CONFIG.write_text(
            json.dumps({"servers": servers}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, PermissionError, TypeError):
        pass


def _send(proc: subprocess.Popen, msg: dict) -> dict | None:
    try:
        payload = json.dumps(msg) + "\n"
        proc.stdin.write(payload)
        proc.stdin.flush()
    except Exception as e:
        return {"error": f"Write error: {e}"}

    try:
        line = proc.stdout.readline()
        if not line:
            return {"error": "Empty response from server"}
        return json.loads(line)
    except Exception as e:
        return {"error": f"Read error: {e}"}


def _rpc_id():
    _rpc_id.counter += 1
    return _rpc_id.counter


_rpc_id.counter = 0


def start_server(name: str, cmd: str, args: list[str], env: dict | None = None) -> str | None:
    if name in _servers:
        return None

    try:
        import os as _os
        merged_env = dict(env or {})
        _default_path = _os.environ.get("PATH", _os.defpath)
        merged_env.setdefault("PATH", _default_path)
        proc = subprocess.Popen(
            [cmd] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=merged_env,
        )
    except FileNotFoundError:
        return f"Command not found: {cmd}"
    except Exception as e:
        return f"Failed to start {name}: {e}"

    init_req = {
        "jsonrpc": "2.0",
        "id": _rpc_id(),
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fluxlite", "version": "0.5.7"},
        },
    }
    resp = _send(proc, init_req)
    if resp is None or resp.get("error"):
        try:
            proc.terminate()
        except OSError:
            pass
        return f"Initialize failed: {resp}"

    _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    list_req = {
        "jsonrpc": "2.0",
        "id": _rpc_id(),
        "method": "tools/list",
        "params": {},
    }
    resp = _send(proc, list_req)
    tools = []
    if resp and "result" in resp:
        tools = resp["result"].get("tools", [])

    _servers[name] = {
        "process": proc,
        "tools": tools,
        "label": f"{name} ({cmd})",
    }
    return None


def stop_server(name: str):
    server = _servers.pop(name, None)
    if server:
        try:
            server["process"].terminate()
            server["process"].wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            pass


def stop_all():
    for name in list(_servers.keys()):
        stop_server(name)


def init_all() -> list[str]:
    servers = load_config()
    errors = []
    for s in servers:
        name = s.get("name", "?")
        err = start_server(
            name=name,
            cmd=s.get("command", ""),
            args=s.get("args", []),
            env=s.get("env"),
        )
        if err:
            errors.append(f"  {name}: {err}")
    _initialized = True
    return errors


def get_tool_list() -> list[dict]:
    result = []
    for srv_name, srv in _servers.items():
        for t in srv.get("tools", []):
            result.append({
                "server": srv_name,
                "name": t.get("name", "?"),
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {}),
            })
    return result


def call_tool(server: str, tool_name: str, arguments: dict) -> str:
    server_info = _servers.get(server)
    if not server_info:
        available = ", ".join(_servers.keys()) if _servers else "none"
        return f"[mcp] Server '{server}' not running. Available: {available}"

    proc = server_info["process"]
    req = {
        "jsonrpc": "2.0",
        "id": _rpc_id(),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = _send(proc, req)
    if resp is None:
        return "[mcp] No response from server"
    if "error" in resp:
        return f"[mcp] Error: {resp['error']}"

    result = resp.get("result", {})
    content = result.get("content", [])
    output_parts = []
    for item in content:
        if item.get("type") == "text":
            output_parts.append(item.get("text", ""))
        elif item.get("type") == "resource":
            output_parts.append(f"[resource: {item.get('uri', '?')}]")
        else:
            output_parts.append(str(item))
    return "\n".join(output_parts) if output_parts else "[mcp] (empty result)"


def get_server_names() -> list[str]:
    return list(_servers.keys())
