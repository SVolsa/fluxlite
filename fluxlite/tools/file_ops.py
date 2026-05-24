import os
from pathlib import Path

from .sandbox import resolve_path as _sandbox_resolve
WINDOWS_BLOCKED = [
    Path("C:\\Windows"),
    Path("C:\\Program Files"),
    Path("C:\\Program Files (x86)"),
    Path("C:\\System32"),
    Path("C:\\Users\\All Users"),
]
UNIX_BLOCKED = [
    Path("/etc"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
    Path("/boot"),
    Path("/root"),
]


def _is_safe(path: Path) -> tuple[bool, str]:
    resolved = path.resolve()
    if os.name == "nt":
        for blocked in WINDOWS_BLOCKED:
            try:
                resolved.relative_to(blocked)
                return False, f"Access denied: {blocked} is a system directory"
            except ValueError:
                continue
    else:
        for blocked in UNIX_BLOCKED:
            try:
                resolved.relative_to(blocked)
                return False, f"Access denied: {blocked} is a system directory"
            except ValueError:
                continue
    return True, ""

def _safe_path(path_str: str) -> tuple[Path, str]:
    p = Path(path_str).resolve()
    safe, msg = _is_safe(p)
    if not safe:
        raise PermissionError(msg)
    return p, msg


def write(path: str, content: str) -> str:
    p, _ = _safe_path(_sandbox_resolve(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"[file] Written {len(content)} chars to {p}"


def read(path: str) -> str:
    sandboxed = _sandbox_resolve(path)
    p, _ = _safe_path(sandboxed)
    if p.exists():
        return p.read_text(encoding="utf-8")
    p, _ = _safe_path(path)
    if not p.exists():
        return f"[file] File not found: {p}"
    return p.read_text(encoding="utf-8")


def edit(path: str, old_string: str, new_string: str) -> str:
    p, _ = _safe_path(_sandbox_resolve(path))
    if not p.exists():
        return f"[file] File not found: {p}"
    content = p.read_text(encoding="utf-8")
    if old_string not in content:
        return f"[file] old_string not found in {p}"
    new_content = content.replace(old_string, new_string, 1)
    p.write_text(new_content, encoding="utf-8")
    return f"[file] Replaced 1 occurrence in {p}"


def append(path: str, content: str) -> str:
    p, _ = _safe_path(_sandbox_resolve(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(content)
    return f"[file] Appended {len(content)} chars to {p}"


def delete(path: str) -> str:
    p, _ = _safe_path(_sandbox_resolve(path))
    if not p.exists():
        return f"[file] File not found: {p}"
    p.unlink()
    return f"[file] Deleted {p}"


def list_dir(path: str = ".", pattern: str = "") -> str:
    p, _ = _safe_path(_sandbox_resolve(path))
    if not p.exists():
        return f"[file] Directory not found: {p}"
    if not p.is_dir():
        return f"[file] Not a directory: {p}"

    if pattern:
        items = sorted(p.glob(pattern))
    else:
        items = sorted(p.iterdir())

    if not items:
        return f"[file] No files matching '{pattern}' in {p}"

    result = []
    for item in items:
        suffix = "/" if item.is_dir() else ""
        size = item.stat().st_size if item.is_file() else 0
        if size:
            size_str = _format_size(size)
            result.append(f"  {item.name}{suffix} ({size_str})")
        else:
            result.append(f"  {item.name}{suffix}")
    return "\n".join(result)


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
