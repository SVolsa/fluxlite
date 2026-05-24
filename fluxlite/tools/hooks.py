"""Hook system: run user-defined scripts before/after tool execution.

Scripts are placed in ~/.fluxlite/hooks/{direction}_{tool_name}/ or {direction}_all/.
Receives context via environment variables (FLUXLITE_TOOL_NAME, etc.).
"""
import json
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path.home() / ".fluxlite" / "hooks"
DEFAULT_TIMEOUT = 10


def _is_executable(path: Path) -> bool:
    if not path.is_file():
        return False
    if sys.platform == "win32":
        return path.suffix.lower() in (".bat", ".cmd", ".exe", ".ps1", ".py")
    return bool(path.stat().st_mode & 0o111)


def _discover(direction: str, tool_name: str) -> list[Path]:
    scripts = []
    for subdir in [f"{direction}_{tool_name}", f"{direction}_all"]:
        d = HOOKS_DIR / subdir
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if _is_executable(f):
                    scripts.append(f)
    return scripts


def _build_env(tool_name: str, args: dict, result: str = None, direction: str = "pre") -> dict:
    env = {
        "FLUXLITE_TOOL_NAME": tool_name,
        "FLUXLITE_TOOL_ARGS": json.dumps(args, ensure_ascii=False),
        "FLUXLITE_HOOK_DIRECTION": direction,
        "FLUXLITE_PROJECT_DIR": str(Path.cwd()),
    }
    if result is not None:
        env["FLUXLITE_TOOL_RESULT"] = result[:10000]
    return env


def _run_script(script: Path, env: dict, timeout: int = DEFAULT_TIMEOUT) -> str:
    try:
        import os as _os
        merged_env = _os.environ.copy()
        merged_env.update(env)
        r = subprocess.run(
            [str(script)],
            capture_output=True, text=True, timeout=timeout,
            env=merged_env,
        )
        parts = []
        if r.stdout.strip():
            parts.append(r.stdout.strip())
        if r.stderr.strip():
            parts.append(f"[stderr]\n{r.stderr.strip()}")
        if r.returncode != 0:
            parts.append(f"(exit {r.returncode})")
        return "\n".join(parts) if parts else ""
    except subprocess.TimeoutExpired:
        return f"[hook] {script.name} timed out after {timeout}s"
    except Exception as e:
        return f"[hook] {script.name} error: {e}"


def run_pre(tool_name: str, args: dict) -> str:
    scripts = _discover("pre", tool_name)
    if not scripts:
        return ""
    env = _build_env(tool_name, args, direction="pre")
    outputs = []
    for s in scripts:
        out = _run_script(s, env)
        if out:
            outputs.append(f"[pre/{s.name}]\n{out}")
    return "\n".join(outputs)


def run_post(tool_name: str, args: dict, result: str) -> str:
    scripts = _discover("post", tool_name)
    if not scripts:
        return ""
    env = _build_env(tool_name, args, result=result, direction="post")
    outputs = []
    for s in scripts:
        out = _run_script(s, env)
        if out:
            outputs.append(f"[post/{s.name}]\n{out}")
    return "\n".join(outputs)


def list_hooks() -> str:
    if not HOOKS_DIR.is_dir():
        return "No hooks directory (~/.fluxlite/hooks/)"
    lines = []
    for subdir in sorted(HOOKS_DIR.iterdir()):
        if subdir.is_dir():
            scripts = [f.name for f in sorted(subdir.iterdir()) if _is_executable(f)]
            if scripts:
                lines.append(f"  {subdir.name}/")
                for s in scripts:
                    lines.append(f"    - {s}")
    if not lines:
        return "No hook scripts found in ~/.fluxlite/hooks/"
    return "\n".join(lines)


def run_single(hook_name: str, args: str = "{}") -> str:
    if not HOOKS_DIR.is_dir():
        return f"Hooks directory not found at {HOOKS_DIR}"

    parsed_args = {}
    if args:
        try:
            parsed_args = json.loads(args)
        except json.JSONDecodeError:
            pass

    category_dir = HOOKS_DIR / hook_name
    if category_dir.is_dir():
        scripts = sorted(category_dir.iterdir())
        env = _build_env(hook_name, parsed_args)
        outputs = []
        for s in scripts:
            if _is_executable(s):
                out = _run_script(s, env)
                if out:
                    outputs.append(f"[{s.name}]\n{out}")
        return "\n".join(outputs) if outputs else f"No executable hooks in {hook_name}/"

    for subdir in HOOKS_DIR.iterdir():
        if subdir.is_dir():
            script = subdir / hook_name
            if script.exists() and _is_executable(script):
                env = _build_env(hook_name, parsed_args)
                return _run_script(script, env)

    return f"Hook '{hook_name}' not found"


def hook_run_handler(hook_name: str, args: str = "{}") -> str:
    return run_single(hook_name, args)


def hook_list_handler() -> str:
    return list_hooks()
