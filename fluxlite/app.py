import sys
import json
import time
import threading
import itertools
from datetime import datetime
from pathlib import Path

from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style

from .i18n import _, set_lang
from .styles import (
    CYAN, GREEN, PURPLE, ORANGE, RED, BLUE, GRAY, DIM, GRAY_LIGHT,
)
from .tools.registry import get_tool_schemas, execute_tool
from .provider import create_provider
from .memory import load_memory, save_memory
from .commands import CommandState, handle_command, MODEL_PRESETS
from .console import console, read_multiline as read_input

HISTORY_DIR = Path.home() / ".fluxlite" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = HISTORY_DIR / "latest.json"
_LAST_SAVE = 0.0
_SAVE_DEBOUNCE = 2.0


class _Spinner:
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self, message):
        self._running = True
        self._message = message
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        for c in itertools.cycle('|/-\\'):
            if not self._running:
                break
            sys.stdout.write(f'\r  {c} {self._message} ')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(0.3)
        self._thread = None


def _now():
    return datetime.now().strftime("%H:%M")


def _print_user(msg: str):
    ts = _now()
    console.print(f"\n[{GREEN}]You[/]  [{GRAY}]{ts}[/]")
    console.print(Text(msg, style=Style(color=GRAY_LIGHT)))


def _stream_char(char: str):
    try:
        sys.stdout.write(char)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write(char.encode("utf-8"))
        except Exception:
            console.out(char, end="")
    sys.stdout.flush()


def _setup_identity(memory):
    identity = memory.get("identity", {})
    if identity.get("name"):
        return identity["name"], identity.get("user_name", "")

    console.print(f"\n  [{CYAN}]Identity Setup (首次设置身份)[/]")
    console.print(f"  [{GRAY}]Let's get to know each other![/]")

    user_name = get_input(f"  [{GREEN}]What should I call you? (如何称呼你)[/]: ")
    memory["identity"]["user_name"] = user_name.strip() if user_name.strip() else "User"

    name = get_input(f"  [{CYAN}]What would you like to name me? (给我取个名字)[/]: ")
    memory["identity"]["name"] = name.strip() if name.strip() else "FluxLite"

    personality = get_input(f"  [{PURPLE}]Describe my personality (optional / 描述我的性格)[/]: ")
    memory["identity"]["personality"] = personality.strip() if personality.strip() else ""

    memory["identity"]["created_at"] = datetime.now().isoformat()
    save_memory(memory)
    return memory["identity"]["name"], memory["identity"]["user_name"]


def _save_session(messages):
    global _LAST_SAVE
    now = time.time()
    if now - _LAST_SAVE < _SAVE_DEBOUNCE:
        return
    _LAST_SAVE = now
    try:
        data = []
        for m in messages:
            if m["role"] == "system":
                continue
            entry = {"role": m["role"], "content": m.get("content", "")}
            if m.get("tool_calls"):
                entry["tool_calls"] = [
                    {"function": {"name": tc.get("function", {}).get("name", ""), "arguments": tc.get("function", {}).get("arguments", "")}}
                    for tc in m["tool_calls"]
                ]
            data.append(entry)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_session():
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass
    return None


def build_system_prompt(lang: str, safe_mode: bool, tools: list, memory: dict = None) -> str:
    lines = []
    for t in tools:
        params = ", ".join(
            f"{k}: {v.get('type', 'str')}" for k, v in t.get("parameters", {}).items()
        )
        lines.append(f"- {t['name']}({params}): {t.get('description', '')}")
    tool_desc = "\n".join(lines)

    identity = (memory or {}).get("identity", {})
    agent_name = identity.get("name", "FluxLite") or "FluxLite"
    user_name = identity.get("user_name", "User")
    personality = identity.get("personality", "")
    rules_list = (memory or {}).get("rules", [])

    identity_block = ""
    if identity.get("name"):
        if lang == "zh":
            identity_block = f"\n你的名字是 {agent_name}。"
            if user_name and user_name != "User":
                identity_block += f"\n用户的名字是 {user_name}，请用此称呼用户。"
            if personality:
                identity_block += f"\n性格: {personality}"
        else:
            identity_block = f"\nYour name is {agent_name}."
            if user_name and user_name != "User":
                identity_block += f"\nUser's name is {user_name}, address them by this name."
            if personality:
                identity_block += f"\nPersonality: {personality}"

    rules_block = ""
    if rules_list:
        if lang == "zh":
            rules_block = "\n\n用户注意事项:\n" + "\n".join(f"- {r}" for r in rules_list)
        else:
            rules_block = "\n\nUser rules:\n" + "\n".join(f"- {r}" for r in rules_list)

    if lang == "zh":
        return f"""你是 {agent_name}，一个运行在终端的轻量级 AI agent。
你可以使用以下工具：

{tool_desc}

规则：
- 需要用工具时调用工具
- 调用格式通过 function calling
- 回复简洁直接
- 用中文回答{identity_block}{rules_block}"""
    return f"""You are {agent_name}, a lightweight AI agent running in the terminal.
Available tools:

{tool_desc}

Rules:
- Call tools using function calling when needed
- Keep responses concise
- Answer in English{identity_block}{rules_block}"""


def _stream_response(provider, messages, tool_schemas, agent_name, max_retries=3):
    content = ""
    reasoning = ""
    tool_calls = []
    usage = None
    streamed = False
    received = False
    reasoning_header_shown = False

    spinner = _Spinner()
    spinner.start(_("responding"))

    for attempt in range(max_retries):
        try:
            for chunk in provider.chat_stream(messages, tool_schemas):
                if not received:
                    received = True
                    spinner.stop()
                if chunk.usage:
                    usage = chunk.usage
                elif chunk.tool_calls:
                    tool_calls = chunk.tool_calls
                elif chunk.reasoning_content:
                    reasoning += chunk.reasoning_content
                    if CommandState.thinking_mode != "off" and not reasoning_header_shown:
                        console.print(f"\n  [{DIM}]\u2501\u2501 {_('thinking')} \u2501\u2501[/]")
                        reasoning_header_shown = True
                elif chunk.content:
                    if not streamed:
                        ts = _now()
                        console.print(f"\n[{CYAN}]{agent_name}[/]  [{GRAY}]{ts}[/]")
                        streamed = True
                    if reasoning and CommandState.thinking_mode == "visible":
                        console.print(f"  [{DIM}]\u2501\u2501 Reasoning \u2501\u2501[/]")
                        console.print(Text(reasoning, style=Style(color=DIM)))
                        console.print(f"  [{DIM}]\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501[/]")
                        reasoning = ""
                    content += chunk.content
                    _stream_char(chunk.content)
            return dict(content=content, reasoning=reasoning, tool_calls=tool_calls, usage=usage, received=received, streamed=streamed, truncated=False)
        except KeyboardInterrupt:
            console.print(f"\n  [{ORANGE}]! {_('truncated')}[/]")
            return dict(content=content, reasoning=reasoning, tool_calls=tool_calls, usage=usage, received=received, streamed=streamed, truncated=True)
        except Exception as e:
            if attempt < max_retries - 1:
                if not received:
                    spinner.stop()
                console.print(f"\n  [{ORANGE}]! {e}")
                console.print(f"  [{ORANGE}]! Retry {attempt + 2}/{max_retries}...[/]")
                spinner.start(_("responding"))
                received = False
                time.sleep(1)
                continue
            if not received:
                spinner.stop()
            console.print(f"\n  [{RED}]x {e}[/]")
            return dict(content=content, reasoning=reasoning, tool_calls=tool_calls, usage=usage, received=received, streamed=streamed, truncated=False)
    spinner.stop()
    return dict(content="", reasoning="", tool_calls=[], usage=None, received=False, streamed=False, truncated=False)


def run_app(
    api_key: str,
    base_url: str,
    model: str,
    tavily_key: str,
    timeout: int = 60,
    safe_mode: bool = True,
    lang: str = "zh",
):
    set_lang(lang)

    memory = load_memory()
    agent_name, user_name = _setup_identity(memory)

    provider = create_provider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        tools_enabled=True,
    )

    tool_schemas = get_tool_schemas()
    system_prompt = build_system_prompt(lang, safe_mode, tool_schemas, memory)
    messages = [{"role": "system", "content": system_prompt}]

    session = _load_session()
    if session:
        messages.extend(session)
        seen = 0
        for msg in session:
            role = msg["role"]
            if role == "user":
                _print_user(msg.get("content", ""))
                seen += 1
            elif role == "assistant":
                content = msg.get("content", "")
                if content:
                    console.print(f"\n[{CYAN}]{agent_name}[/]  [{GRAY}]{_now()}[/]")
                    console.print(Markdown(content, code_theme="monokai"))
                seen += 1
        console.print()

    console.print(f"  [{GRAY}]model: {model}     /help  /tools  /memory  /exit[/]")
    console.print(f"  [{GRAY}]{'='*45}[/]")

    while True:
        try:
            console.print(f"\n  [{CYAN}]──────────────────── Input  ────────────────────[/]")
            user_input = read_input(f"  ")
            console.print(f"  [{CYAN}]────────────────────────────────────────────────[/]")
        except (EOFError, KeyboardInterrupt):
            console.print()
            continue

        if 'user_input' not in locals():
            continue

        # Strip trailing newlines (from Enter=newline input behavior)
        while user_input.endswith("\n"):
            user_input = user_input[:-1]
        user_input = user_input.strip()
        if not user_input:
            continue

        sys.stdout.write('\033[4A\033[J')
        sys.stdout.flush()

        if user_input.startswith("/"):
            should_exit = handle_command(user_input, messages, model, provider)
            if should_exit:
                _save_session(messages[1:])
                break
            continue

        messages.append({"role": "user", "content": user_input})
        _print_user(user_input)

        turn = 0
        while turn < 10:
            turn += 1

            result = _stream_response(provider, messages, tool_schemas, agent_name, max_retries=3)

            assistant_content = result.get("content", "")
            assistant_reasoning = result.get("reasoning", "")
            pending_tool_calls = result.get("tool_calls", [])
            last_usage = result.get("usage")
            received = result.get("received", False)
            truncated = result.get("truncated", False)
            streamed = result.get("streamed", False)

            if not received:
                console.print(f"\n  [{ORANGE}]! {_('error')}: AI returned empty response[/]")
                _save_session(messages[1:])
                break

            if CommandState.show_token_usage and last_usage:
                usage_str = ""
                if "prompt_tokens" in last_usage:
                    usage_str += f"in: {last_usage['prompt_tokens']}  "
                if "completion_tokens" in last_usage:
                    usage_str += f"out: {last_usage['completion_tokens']}  "
                if "total_tokens" in last_usage:
                    usage_str += f"total: {last_usage['total_tokens']}"
                if "input_tokens" in last_usage:
                    usage_str += f"in: {last_usage['input_tokens']}  "
                if "output_tokens" in last_usage:
                    usage_str += f"out: {last_usage['output_tokens']}  "
                if usage_str:
                    console.print(f"  [{DIM}]\u2502 {usage_str}[/]")

            if not pending_tool_calls:
                if assistant_content and not streamed:
                    ts = _now()
                    console.print(f"\n[{CYAN}]{agent_name}[/]  [{GRAY}]{ts}[/]")
                    console.print(Markdown(assistant_content, code_theme="monokai"))
                msg = {"role": "assistant", "content": assistant_content}
                if assistant_reasoning:
                    msg["reasoning_content"] = assistant_reasoning
                messages.append(msg)
                _save_session(messages[1:])
                break

            openai_tool_calls = []
            for tc in pending_tool_calls:
                openai_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                })

            if assistant_content and not streamed:
                console.print(f"\n[{CYAN}]{agent_name}[/]  [{GRAY}]{_now()}[/]")
                console.print(Markdown(assistant_content, code_theme="monokai"))

            msg = {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": openai_tool_calls,
            }
            if assistant_reasoning:
                msg["reasoning_content"] = assistant_reasoning
            messages.append(msg)

            for tc in pending_tool_calls:
                args_str = ", ".join(f"{k}={v}" for k, v in tc.arguments.items())
                console.print(f"\n  [{ORANGE}]{tc.name}({args_str})[/]")
                s = _Spinner()
                s.start(_("processing"))
                try:
                    result = execute_tool(tc.name, tc.arguments)
                finally:
                    s.stop()
                if CommandState.show_tool_result:
                    console.print(Text(result[:2000], style=Style(color=GRAY_LIGHT)))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            pending_tool_calls = []

        if turn >= 10:
            console.print(f"  [{ORANGE}]Max turns reached[/]")
