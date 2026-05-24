"""Test runner tool for running and parsing test output."""
import shlex
import subprocess
import re
from pathlib import Path

_TIMEOUT = 120


def run_tests(command: str, path: str = ".", timeout: int = _TIMEOUT) -> str:
    root = Path(path).resolve()
    if not root.exists():
        return f"[error] Path not found: {path}"
    if not root.is_dir():
        return f"[error] Not a directory: {path}"

    try:
        argv = shlex.split(command)
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=root,
        )
    except subprocess.TimeoutExpired:
        return f"[error] Tests timed out after {timeout}s"
    except Exception as e:
        return f"[error] Failed to run tests: {e}"

    stdout = result.stdout
    stderr = result.stderr
    rc = result.returncode

    output_parts = ["[test output]"]

    summary = ""
    for line in (stdout + stderr).split("\n"):
        line_stripped = line.strip()
        if re.match(r"^=+.*\d+\s+(passed|failed|error).*=+$", line_stripped):
            summary = line_stripped
        elif re.match(r"^Ran \d+ test", line_stripped):
            summary = line_stripped
        elif line_stripped in ("OK", "FAILED") and summary:
            summary += f"  [{line_stripped}]"

    if summary:
        output_parts.append(f"  {summary}")
    else:
        output_parts.append(f"  exit code: {rc}")

    failure_lines = []
    capture = False
    for line in stdout.split("\n"):
        if re.match(r"^(FAILED|ERRORS|FAILURES)", line):
            capture = True
        if capture:
            failure_lines.append(line.strip())

    if failure_lines:
        output_parts.append("")
        for fl in failure_lines[:30]:
            output_parts.append(f"  {fl}")
        if len(failure_lines) > 30:
            output_parts.append(f"  ... ({len(failure_lines) - 30} more failure lines)")

    if stderr.strip():
        output_parts.append("")
        for line in stderr.strip().split("\n")[:20]:
            output_parts.append(f"  {line}")

    stdout_clean = stdout.strip()
    if stdout_clean and not summary and not failure_lines:
        lines = stdout_clean.split("\n")[:40]
        output_parts.extend(["  " + l for l in lines])

    if result.returncode != 0 and not summary and not stderr.strip() and not stdout_clean:
        output_parts.append(f"[error] Tests failed with exit code {result.returncode}")

    output_parts.append(f"\n[exit code: {result.returncode}]")
    return "\n".join(output_parts)
