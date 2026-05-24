"""Git operation tools for AI use."""
import subprocess
from pathlib import Path

_TIMEOUT = 15


def _run_git(*args: str) -> tuple[str, str, int]:
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=_TIMEOUT,
            cwd=Path.cwd(),
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "git not found", -1
    except subprocess.TimeoutExpired:
        return "", "timed out", -1


def status_handler() -> str:
    stdout, stderr, rc = _run_git("status", "--short")
    if rc != 0:
        return f"[error] {stderr.strip()}"
    branch, _, _ = _run_git("branch", "--show-current")
    branch_str = branch.strip() if branch.strip() else "(detached HEAD)"
    return f"Branch: {branch_str}\n{stdout}" if stdout.strip() else f"Branch: {branch_str}\n(clean working tree)"


def diff_handler(path: str = "", staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if path:
        args.append(path)
    stdout, stderr, rc = _run_git(*args)
    if rc != 0:
        return f"[error] {stderr.strip()}"
    if not stdout.strip():
        return "No changes."
    if len(stdout) > 3000:
        stdout = stdout[:3000] + "\n... (truncated at 3000 chars)"
    return stdout


def log_handler(count: int = 10) -> str:
    stdout, stderr, rc = _run_git("log", f"-{count}", "--oneline", "--decorate")
    if rc != 0:
        return f"[error] {stderr.strip()}"
    return stdout.strip() or "No commits."


def add_handler(path: str = ".") -> str:
    stdout, stderr, rc = _run_git("add", path)
    if rc != 0:
        return f"[error] {stderr.strip()}"
    return f"Staged: {path}"


def commit_handler(message: str, auto_add: bool = True) -> str:
    if auto_add:
        _run_git("add", "-A")
    stdout, stderr, rc = _run_git("commit", "-m", message)
    if rc != 0:
        return f"[error] {stderr.strip()}"
    return stdout.strip()
