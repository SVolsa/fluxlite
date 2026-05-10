import sys

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings

console = Console()

_input_history = InMemoryHistory()
_bindings = KeyBindings()

# Enter = submit, Esc+Enter = newline (multi-line)
# Note: Shift+Enter is indistinguishable from Enter at terminal level.
@_bindings.add("enter")
def _(event):
    event.current_buffer.validate_and_handle()


@_bindings.add("escape", "enter")
def _(event):
    event.current_buffer.insert_text("\n")


# Lazy-init sessions (avoid prompt_toolkit console detection at import time)
_multiline_session = None
_single_session = None


def _get_multiline_session():
    global _multiline_session
    if _multiline_session is None:
        _multiline_session = PromptSession(
            history=_input_history,
            key_bindings=_bindings,
            multiline=True,
        )
    return _multiline_session


def _get_single_session():
    global _single_session
    if _single_session is None:
        _single_session = PromptSession(
            history=_input_history,
            multiline=False,
        )
    return _single_session


def get_input(prompt: str = "") -> str:
    try:
        return _get_single_session().prompt(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def read_multiline(prompt: str) -> str:
    try:
        return _get_multiline_session().prompt(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""
