import subprocess
import sys

BLOCKED_KEYWORDS = [
    "shutdown", "reboot", "halt", "poweroff",
    "format", "mkfs", "dd if=", ":(){ :|:& };:",
    "import os; os.remove", "__import__('os').system",
]

MAX_OUTPUT_LINES = 2000
TIMEOUT = 30


def _check_blocked(code: str) -> bool:
    code_lower = code.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in code_lower:
            return True
    return False


def execute(language: str, code: str) -> str:
    if _check_blocked(code):
        return "[error] Blocked: potentially destructive command detected"

    if language == "python":
        try:
            import ast
            ast.parse(code)
        except SyntaxError as e:
            return f"[error] Syntax error: {e}"

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"[error] Execution timed out after {TIMEOUT}s"
        except Exception as e:
            return f"[error] Execution error: {e}"

    elif language == "bash":
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"[error] Execution timed out after {TIMEOUT}s"
        except Exception as e:
            return f"[error] Execution error: {e}"

    else:
        return f"[error] Unsupported language: {language} (use python or bash)"

    output_parts = []

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

    return "\n".join(output_parts)
