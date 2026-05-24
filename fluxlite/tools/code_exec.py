"""Code execution tool with auto-linting for Python.

Supports arbitrary shell commands (npm, cargo, go, curl, etc.)."""
import subprocess
import sys
import ast
import re

from .sandbox import _SandboxState

DESTRUCTIVE_PATTERNS = [
    re.compile(r'\bshutdown\b'),
    re.compile(r'\breboot\b'),
    re.compile(r'\bhalt\b'),
    re.compile(r'\bpoweroff\b'),
    re.compile(r'\bmkfs\b'),
    re.compile(r'\bdd\s+if='),
    re.compile(r':\s*\(\s*\)\s*\{'),
    re.compile(r'\brm\s+-(?:rf|fr|r\s+-\s*f)\s+[/~.]'),
    re.compile(r'\bdel\s+/[FfQq].*\b'),
    re.compile(r'\brd\s+/[SsQq].*\b'),
    re.compile(r'\bformat\s+[A-Za-z]:'),
    re.compile(r'>\s*/dev/sd'),
    re.compile(r'\bchmod\s+.*777\s+/'),
]

MAX_OUTPUT_LINES = 2000
DEFAULT_TIMEOUT = 30


def _check_blocked(code: str) -> bool:
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern.search(code):
            return True
    return False


def _run_lint(code: str) -> str:
    issues = []

    try:
        ast.parse(code)
    except SyntaxError as e:
        return f"[lint] SyntaxError: {e}"

    try:
        compile(code, "<check>", "exec")
    except SyntaxError as e:
        issues.append(f"[lint] SyntaxError: {e}")
    except ValueError as e:
        issues.append(f"[lint] ValueError: {e}")

    for linter, cmd in [
        ("pyflakes", [sys.executable, "-m", "pyflakes", "-"]),
        ("pyright", ["pyright", "--outputjson", "-"]),
        ("mypy", [sys.executable, "-m", "mypy", "--ignore-missing-imports", "-"]),
    ]:
        try:
            r = subprocess.run(
                cmd,
                input=code,
                capture_output=True, text=True, timeout=10,
            )
            stderr = (r.stderr or "").strip()
            stdout = (r.stdout or "").strip()
            if stderr:
                for line in stderr.split("\n")[:8]:
                    issues.append(f"[{linter}] {line}")
            if stdout:
                for line in stdout.split("\n")[:8]:
                    issues.append(f"[{linter}] {line}")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

    if not issues:
        return "[lint] OK"
    return "\n".join(issues[:12])


def execute(language: str, code: str, workdir: str = None, timeout: int = None) -> str:
    if _check_blocked(code):
        return "[error] Blocked: potentially destructive command detected"

    exec_timeout = timeout or DEFAULT_TIMEOUT
    if workdir:
        cwd = workdir
    else:
        cwd = str(_SandboxState.get_sandbox_dir()) if _SandboxState.is_active() else None

    output_parts = []

    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"[error] Syntax error: {e}"

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return f"[error] Execution timed out after {exec_timeout}s"
        except Exception as e:
            return f"[error] Execution error: {e}"

        if result.stdout:
            lines = result.stdout.rstrip().split("\n")
            if len(lines) > MAX_OUTPUT_LINES:
                lines = lines[:MAX_OUTPUT_LINES]
                lines.append(f"... ({len(lines) - MAX_OUTPUT_LINES} more lines)")
            output_parts.append("[output]\n" + "\n".join(lines))

        if result.stderr:
            lines = result.stderr.rstrip().split("\n")
            if len(lines) > MAX_OUTPUT_LINES:
                lines = lines[:MAX_OUTPUT_LINES]
                lines.append(f"... ({len(lines) - MAX_OUTPUT_LINES} more lines)")
            output_parts.append("[stderr]\n" + "\n".join(lines))

        if result.returncode != 0:
            output_parts.append(f"[error] Exit code: {result.returncode}")

        if not output_parts:
            output_parts.append("[output] (no output)")

        lint = _run_lint(code)
        output_parts.append(f"\n[lint]\n{lint}")

    elif language in ("bash", "shell"):
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return f"[error] Execution timed out after {exec_timeout}s"
        except Exception as e:
            return f"[error] Execution error: {e}"

        if result.stdout:
            lines = result.stdout.rstrip().split("\n")
            if len(lines) > MAX_OUTPUT_LINES:
                lines = lines[:MAX_OUTPUT_LINES]
                lines.append(f"... ({len(lines) - MAX_OUTPUT_LINES} more lines)")
            output_parts.append("[output]\n" + "\n".join(lines))

        if result.stderr:
            lines = result.stderr.rstrip().split("\n")
            if len(lines) > MAX_OUTPUT_LINES:
                lines = lines[:MAX_OUTPUT_LINES]
                lines.append(f"... ({len(lines) - MAX_OUTPUT_LINES} more lines)")
            output_parts.append("[stderr]\n" + "\n".join(lines))

        if result.returncode != 0:
            output_parts.append(f"[error] Exit code: {result.returncode}")

        if not output_parts:
            output_parts.append("[output] (no output)")

    else:
        return f"[error] Unsupported language: {language} (use python, bash, or shell)"

    return "\n".join(output_parts)
