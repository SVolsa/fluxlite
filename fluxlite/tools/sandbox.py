"""Sandbox: isolate file operations and command execution in a temp directory.

When sandbox mode is enabled:
- file_write/edit/append/delete → redirected to a temp directory
- code_executor working directory → sandbox temp dir
- Read falls back to original project if file not in sandbox

Use /sandbox <on|off|review|apply|discard|status> to control.
"""
import difflib
import shutil
import tempfile
from pathlib import Path


class _SandboxState:
    enabled: bool = False
    _temp_dir: Path | None = None
    _original_cwd: Path | None = None

    @classmethod
    def enable(cls) -> Path:
        if cls._temp_dir is None:
            cls._temp_dir = Path(tempfile.mkdtemp(prefix="fluxlite_sandbox_"))
        cls._original_cwd = Path.cwd()
        cls.enabled = True
        return cls._temp_dir

    @classmethod
    def disable(cls):
        cls.enabled = False
        cls._original_cwd = None

    @classmethod
    def is_active(cls) -> bool:
        return cls.enabled and cls._temp_dir is not None

    @classmethod
    def get_sandbox_dir(cls) -> Path | None:
        return cls._temp_dir

    @classmethod
    def resolve_path(cls, path_str: str) -> str:
        if not cls.is_active():
            return path_str
        p = Path(path_str)
        if p.is_absolute():
            rel = p.relative_to(p.anchor) if p.anchor else p
            return str(cls._temp_dir / rel)
        return str(cls._temp_dir / p)

    @classmethod
    def review(cls) -> str:
        if not cls._temp_dir or not cls._original_cwd:
            return "Sandbox not active"
        diffs = []
        for f in cls._temp_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(cls._temp_dir)
                orig = cls._original_cwd / rel
                sandbox_text = f.read_text(encoding="utf-8", errors="replace")
                if orig.exists():
                    orig_text = orig.read_text(encoding="utf-8", errors="replace")
                    if sandbox_text == orig_text:
                        continue
                    diff = difflib.unified_diff(
                        orig_text.splitlines(),
                        sandbox_text.splitlines(),
                        fromfile=str(rel),
                        tofile=str(rel),
                        lineterm="",
                    )
                    diffs.append("\n".join(diff))
                else:
                    diffs.append(f"--- /dev/null\n+++ {rel}\n" + "\n".join(
                        f"+{l}" for l in sandbox_text.splitlines()
                    ))
        if not diffs:
            return "No pending changes in sandbox"
        return "\n\n".join(diffs)

    @classmethod
    def apply(cls) -> str:
        if not cls._temp_dir or not cls._original_cwd:
            return "Sandbox not active"
        count = 0
        for f in cls._temp_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(cls._temp_dir)
                dest = cls._original_cwd / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                count += 1
        return f"Applied {count} file(s) from sandbox to project"

    @classmethod
    def discard(cls) -> str:
        if cls._temp_dir and cls._temp_dir.exists():
            shutil.rmtree(cls._temp_dir)
        cls._temp_dir = Path(tempfile.mkdtemp(prefix="fluxlite_sandbox_"))
        return "Sandbox discarded (fresh empty sandbox created)"

    @classmethod
    def status(cls) -> str:
        if not cls.is_active():
            return "Sandbox: disabled"
        count = 0
        if cls._temp_dir:
            count = sum(1 for _ in cls._temp_dir.rglob("*") if _.is_file())
        return f"Sandbox: enabled  files: {count}  dir: {cls._temp_dir}"


def resolve_path(path_str: str) -> str:
    return _SandboxState.resolve_path(path_str)


def is_active() -> bool:
    return _SandboxState.is_active()
