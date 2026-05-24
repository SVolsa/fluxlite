"""Code search tools: grep and glob for codebase exploration."""
import os
import re
from pathlib import Path


def _should_ignore(name: str) -> bool:
    skip = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".tox", ".egg-info", "dist", "build", ".idea", ".vscode",
        ".mypy_cache", ".pytest_cache", ".ruff_cache", ".DS_Store",
        ".svn", "target", "bin", "obj",
    }
    return name in skip or name.startswith(".")


def grep_handler(pattern: str, path: str = ".", file_glob: str = "", max_results: int = 40) -> str:
    root = Path(path).resolve()
    if not root.exists():
        return f"[error] Path not found: {path}"
    if not root.is_dir():
        return f"[error] Not a directory: {path}"

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"[error] Invalid regex: {e}"

    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_ignore(d)]
        for fn in filenames:
            if _should_ignore(fn):
                continue
            if file_glob and not fn.endswith(file_glob.replace("*", "")):
                continue
            if file_glob and "*" not in file_glob and fn != file_glob:
                continue
            fpath = Path(dirpath) / fn
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if compiled.search(line):
                            rel = fpath.relative_to(root)
                            matches.append(f"{rel}:{i}: {line.rstrip()[:200]}")
                            if len(matches) >= max_results:
                                break
            except Exception:
                continue
        if len(matches) >= max_results:
            break

    if not matches:
        return f"No matches for {pattern!r} in {path}"
    result = "\n".join(matches[:max_results])
    if len(matches) > max_results:
        result += f"\n... ({len(matches) - max_results} more matches)"
    return result


def glob_handler(pattern: str, path: str = ".") -> str:
    root = Path(path).resolve()
    if not root.exists():
        return f"[error] Path not found: {path}"
    if not root.is_dir():
        return f"[error] Not a directory: {path}"

    items = list(root.rglob(pattern))
    items = [i for i in items if not any(
        _should_ignore(p.name) for p in i.relative_to(root).parents
    ) and not _should_ignore(i.name)]

    if not items:
        return f"No files matching {pattern!r} in {path}"

    lines = []
    for i in items[:100]:
        rel = i.relative_to(root)
        suffix = "/" if i.is_dir() else ""
        size = i.stat().st_size if i.is_file() else 0
        size_str = f" ({size}B)" if size else ""
        lines.append(f"  {rel}{suffix}{size_str}")
    if len(items) > 100:
        lines.append(f"  ... ({len(items) - 100} more)")
    return "\n".join(lines)
