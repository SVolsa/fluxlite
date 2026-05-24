"""Interactive terminal sessions — persistent shell for multi-step workflows.

Each session is a long-running shell subprocess. Commands run sequentially
within the session, preserving state (env vars, cwd, venv, etc.).

Uses a dedicated reader thread per session for cross-platform compatibility.
"""

import os
import json
import time
import uuid
import queue
import threading
import subprocess
from pathlib import Path


_sessions: dict[str, "_TerminalSession"] = {}


class _TerminalSession:

    def __init__(self):
        self.id = uuid.uuid4().hex[:8]
        if os.name == "nt":
            shell_path = os.environ.get("COMSPEC", "cmd.exe")
        else:
            shell_path = os.environ.get("SHELL", "/bin/bash")
        self.shell = Path(shell_path).name

        env = os.environ.copy()
        env.setdefault("TERM", "dumb")

        try:
            self.process = subprocess.Popen(
                [shell_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                bufsize=1,
                cwd=str(Path.cwd()),
            )
        except (FileNotFoundError, OSError) as e:
            raise RuntimeError(f"Failed to start terminal: {e}")
        self._alive = True
        self._lock = threading.Lock()
        self._line_queue: queue.Queue[str | None] = queue.Queue()
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
        time.sleep(0.3)
        self._drain()

    def _reader(self):
        try:
            for line in self.process.stdout:
                self._line_queue.put(line)
        except (ValueError, OSError):
            pass
        finally:
            self._line_queue.put(None)

    def _drain(self):
        while True:
            try:
                line = self._line_queue.get_nowait()
                if line is None:
                    return
            except queue.Empty:
                return

    def run(self, command: str, timeout: int = 60) -> str:
        if not self._alive or self.process.poll() is not None:
            self._alive = False
            return "[session terminated]"

        self._drain()

        marker = f"__TERM_{uuid.uuid4().hex[:6]}__"
        full = f"{command} & echo {marker}\n" if os.name == "nt" else f"{command}; echo {marker}\n"

        with self._lock:
            try:
                self.process.stdin.write(full)
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                self._alive = False
                return f"[write error: {e}]"

            output = []
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    output.append("[Timeout]")
                    break

                try:
                    line = self._line_queue.get(timeout=remaining)
                except queue.Empty:
                    output.append("[Timeout]")
                    break

                if line is None:
                    self._alive = False
                    break
                if line.strip() == marker:
                    break
                output.append(line)

        result = "".join(output).strip()
        return result

    def close(self):
        self._alive = False
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
        except (OSError, subprocess.SubprocessError):
            pass


def terminal_handler(
    action: str = "run",
    session_id: str = "",
    command: str = "",
    timeout: int = 60,
) -> str:
    if action == "start":
        session = _TerminalSession()
        _sessions[session.id] = session
        return json.dumps({"session_id": session.id, "shell": session.shell}, ensure_ascii=False)

    if action == "sessions":
        return json.dumps({"sessions": list(_sessions.keys())}, ensure_ascii=False)

    if action == "stop":
        if session_id and session_id in _sessions:
            _sessions[session_id].close()
            del _sessions[session_id]
            return json.dumps({"session_id": session_id, "status": "closed"}, ensure_ascii=False)
        return json.dumps({"error": "session not found"}, ensure_ascii=False)

    if not session_id or session_id not in _sessions:
        session = _TerminalSession()
        _sessions[session.id] = session
        session_id = session.id

    if not command:
        return json.dumps({"session_id": session_id, "output": ""}, ensure_ascii=False)

    output = _sessions[session_id].run(command, timeout=int(timeout))
    return json.dumps({"session_id": session_id, "output": output}, ensure_ascii=False)
