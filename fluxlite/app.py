import unicodedata
import shutil
import sys
import json
import time
import subprocess
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
from .profile import load_profile, save_profile
from .commands import CommandState, handle_command, MODEL_PRESETS, perform_rewind
from .console import console, read_multiline as read_input, get_input as _ask_input, radio_select, check_rewind_flag

HISTORY_DIR = Path.home() / ".fluxlite" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
_SESSION_PATH = None
_SESSION_MAX_FILES = 50
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
            try:
                term_w = shutil.get_terminal_size().columns
            except Exception:
                term_w = 80
            text = f'  {c} {self._message} '
            text = text.ljust(min(term_w - 1, 120))
            sys.stdout.write(f'\r{text}')
            sys.stdout.flush()
            time.sleep(0.1)

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(1.0)
        self._thread = None
        sys.stdout.write('\r\033[2K\r')
        sys.stdout.flush()


def _now():
    return datetime.now().strftime("%H:%M")


def _print_user(msg: str):
    ts = _now()
    console.print(f"\n[{GREEN}]You[/]  [{GRAY}]{ts}[/]")
    console.print(Text(msg, style=Style(color=GRAY_LIGHT)))


def _setup_identity(profile):
    identity = profile.get("identity", {})
    if identity.get("name"):
        return identity["name"], identity.get("user_name", "")

    console.print(f"\n  [{CYAN}]Identity Setup (首次设置身份)[/]")
    console.print(f"  [{GRAY}]Let's get to know each other![/]")

    user_name = _ask_input(f"  [{GREEN}]What should I call you? (如何称呼你)[/]: ")
    profile["identity"]["user_name"] = user_name.strip() if user_name.strip() else "User"

    name = _ask_input(f"  [{CYAN}]What would you like to name me? (给我取个名字)[/]: ")
    profile["identity"]["name"] = name.strip() if name.strip() else "FluxLite"

    personality = _ask_input(f"  [{PURPLE}]Describe my personality (optional / 描述我的性格)[/]: ")
    profile["identity"]["personality"] = personality.strip() if personality.strip() else ""

    profile["identity"]["created_at"] = datetime.now().isoformat()
    save_profile(profile)
    return profile["identity"]["name"], profile["identity"]["user_name"]


def _session_path() -> Path:
    global _SESSION_PATH
    if _SESSION_PATH is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        _SESSION_PATH = HISTORY_DIR / f"{ts}.json"
    return _SESSION_PATH


def _reset_session():
    global _SESSION_PATH
    _SESSION_PATH = None


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
                entry["tool_calls"] = m["tool_calls"]
            if m.get("tool_call_id"):
                entry["tool_call_id"] = m["tool_call_id"]
            if m.get("reasoning_content"):
                entry["reasoning_content"] = m["reasoning_content"]
            data.append(entry)
        path = _session_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _trim_history()
    except (OSError, PermissionError, TypeError, ValueError):
        pass


def _trim_history():
    files = sorted(HISTORY_DIR.glob("*.json"))
    while len(files) > _SESSION_MAX_FILES:
        files[0].unlink()
        files.pop(0)


def _load_session():
    files = sorted(HISTORY_DIR.glob("*.json"))
    if not files:
        return None
    latest = files[-1]
    try:
        with open(latest, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            for msg in data:
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        if "id" not in tc:
                            tc["id"] = f"call_{hash(str(tc)) % 10**7}"
                        if "type" not in tc:
                            tc["type"] = "function"
                if msg.get("role") == "tool" and "tool_call_id" not in msg:
                    msg["tool_call_id"] = "orphan"
            global _SESSION_PATH
            _SESSION_PATH = latest
            return data
    except (OSError, PermissionError, json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


def build_system_prompt(lang: str, safe_mode: bool, tools: list, profile: dict = None) -> str:
    lines = []
    for t in tools:
        params = ", ".join(
            f"{k}: {v.get('type', 'str')}" for k, v in t.get("parameters", {}).items()
        )
        lines.append(f"- {t['name']}({params}): {t.get('description', '')}")
    tool_desc = "\n".join(lines)

    profile = profile or {}
    identity = profile.get("identity", {})
    agent_name = identity.get("name", "FluxLite") or "FluxLite"
    user_name = identity.get("user_name", "User")
    personality = identity.get("personality", "")
    rules_list = profile.get("rules", [])

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

记忆与规则：
- memory_write / memory_read: 保存和查阅长期记忆
- rule_add / rule_remove / rule_list: 管理行为规则

MCP (外部服务集成):
- mcp_list: 查看已连接的 MCP 服务器（数据库、GitHub 等）
- mcp_call: 调用 MCP 服务器上的工具

自我修改:
- config_set: 修改自身设置（语言、模型、安全模式等）

编程工具:
- grep_search / glob_files: 搜索代码和文件
- file_*: 读写编辑文件
- run_tests: 运行测试并解析结果
- code_executor: 执行 Python/Bash/Shell 代码或任意命令（npm, cargo, 等）
- git_*: Git 版本控制操作

基本规则：
- 需要用工具时调用工具
- 对于复杂任务，先规划步骤再执行
- 每次修改文件后确认语法正确
- 回复简洁直接
- 用中文回答{identity_block}{rules_block}"""
    return f"""You are {agent_name}, a lightweight AI agent running in the terminal.
Available tools:

{tool_desc}

Memory & Rules:
- memory_write / memory_read: Save and retrieve long-term memories
- rule_add / rule_remove / rule_list: Manage behavioral rules

MCP (External Service Integration):
- mcp_list: List connected MCP servers (databases, GitHub, etc.)
- mcp_call: Call tools on MCP servers

Self-modification:
- config_set: Modify own settings (language, model, safe mode, etc.)

Programming tools:
- grep_search / glob_files: Search code and files
- file_*: Read, write, edit files
- run_tests: Run tests and parse results
- code_executor: Execute Python/Bash/Shell code or any command (npm, cargo, etc.)
- git_*: Git version control operations

Rules:
- Call tools when needed
- For complex tasks, plan steps first before executing
- Verify syntax after modifying files
- Keep responses concise
- Answer in English{identity_block}{rules_block}"""


from .context import (
    build_fluxlite_md,
    build_project_memory,
    build_instructions_md,
    build_project_tree,
    build_git_context,
)





_confirmed_tools: set[str] = set()
_cumulative_tokens = {"input": 0, "output": 0}

_MODEL_MAX_TOKENS: dict[str, int] = {
    "deepseek-v4-flash": 65536,
    "deepseek-v4-pro": 65536,
    "deepseek-chat": 65536,
    "deepseek-reasoner": 65536,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    "claude-sonnet-4-20250514": 200000,
    "claude-opus-4-20250514": 200000,
    "claude-3-5-haiku-latest": 200000,
    "llama-3.3-70b-versatile": 131072,
    "mixtral-8x7b-32768": 32768,
    "gemma2-9b-it": 8192,
}
_DEFAULT_MAX_TOKENS = 65536


def _get_max_tokens(model: str) -> int:
    if model in _MODEL_MAX_TOKENS:
        return _MODEL_MAX_TOKENS[model]
    for key, val in _MODEL_MAX_TOKENS.items():
        if key in model or model.endswith(key):
            return val
    return _DEFAULT_MAX_TOKENS


def _render_progress_bar(current: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return ""
    pct = current / total
    filled = min(int(pct * width), width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {pct:.0%}"


def _quality_gate(path: str) -> str | None:
    path_lower = path.lower()
    if not path_lower.endswith(".py"):
        return None
    try:
        source = Path(path).read_text(encoding="utf-8")
    except (OSError, PermissionError, UnicodeDecodeError):
        return None
    try:
        ast.parse(source)
    except SyntaxError as e:
        return f"[quality] {path}: {e}"
    return None


def _auto_fix_file(path: str, error_msg: str, provider) -> str | None:
    try:
        source = Path(path).read_text(encoding="utf-8")
    except (OSError, PermissionError, UnicodeDecodeError):
        return None

    ext = Path(path).suffix
    prompt = (
        f"The following file has a syntax error:\n\nError:\n{error_msg}\n\n"
        f"```{ext[1:] if ext else ''}\n{source}\n```\n\n"
        "Fix the syntax error. Return ONLY the corrected code, no explanations, no markdown formatting."
    )

    try:
        result = provider.chat(messages=[{"role": "user", "content": prompt}], tools=[])
        fixed = (result.content or "").strip()
        if not fixed:
            return None
        if fixed.startswith("```"):
            lines = fixed.split("\n")
            if len(lines) >= 3:
                fixed = "\n".join(lines[1:-1]).strip()
        return fixed
    except Exception:
        return None


def _auto_compress(messages: list, max_tok: int):
    total = _cumulative_tokens["input"] + _cumulative_tokens["output"]
    if total < max_tok * 0.88:
        return
    if total < max_tok * 0.95:
        console.print(f"  [{ORANGE}]! Context at {total}/{max_tok} — auto-trimming old tool cycles[/]")
        for i in range(1, len(messages)):
            if messages[i].get("tool_calls"):
                del messages[i]
                while i < len(messages) and messages[i]["role"] == "tool":
                    del messages[i]
                break
        return
    console.print(f"  [{RED}]! Context critical {total}/{max_tok} — removing oldest exchange[/]")
    for i in range(1, len(messages) - 1):
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            del messages[i:i + 2]
            break


def _confirm_tool(name: str, args: dict) -> bool:
    if name in _confirmed_tools:
        return True

    if name == "code_executor":
        lang = args.get("language", "")
        code = args.get("code", "")
        snippet = (code[:300] + "...") if len(code) > 300 else code
        console.print(f"\n  [{ORANGE}]code_executor ({lang})[/]")
        for line in snippet.split("\n")[:8]:
            console.print(f"  [{DIM}]{line}[/]")
    elif name in ("file_write", "file_edit", "file_delete", "file_append", "git_commit"):
        console.print(f"\n  [{ORANGE}]{name}[/]")
        if name == "git_commit":
            console.print(f"  [{DIM}]{args.get('message', '')}[/]")
        else:
            console.print(f"  [{DIM}]{args.get('path', '')}[/]")
    elif name in ("spawn_agents", "terminal", "file_download", "http_request",
                  "browser", "mcp_call", "hook_run"):
        console.print(f"\n  [{ORANGE}]{name}[/]")
        snippet = str(args)[:200]
        console.print(f"  [{DIM}]{snippet}[/]")
    else:
        return True

    choice = radio_select(f"Allow {name}?", [
        ("allow", "Allow once"),
        ("skip", "Skip this call"),
        ("deny", "Deny"),
        ("always", f"Allow all {name} this session"),
    ])

    if choice == "always":
        _confirmed_tools.add(name)
        return "allow"
    if choice is None or choice == "deny":
        return "deny"
    return choice  # "allow" or "skip"


def _stream_response(provider, messages, tool_schemas, agent_name, max_retries=3):
    content = ""
    reasoning = ""
    tool_calls = []
    usage = None
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
                    content += chunk.content

            return dict(content=content, reasoning=reasoning, tool_calls=tool_calls,
                        usage=usage, received=received, truncated=False)
        except KeyboardInterrupt:
            if not received:
                spinner.stop()
            console.print(f"\n  [{ORANGE}]! {_('truncated')}[/]")
            return dict(content=content, reasoning=reasoning, tool_calls=tool_calls,
                        usage=usage, received=received, truncated=True)
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
            return dict(content=content, reasoning=reasoning, tool_calls=tool_calls,
                        usage=usage, received=received, truncated=False)
    spinner.stop()
    return dict(content="", reasoning="", tool_calls=[], usage=None,
                received=False, truncated=False)


def run_app(
    api_key: str,
    base_url: str,
    model: str,
    tavily_key: str,
    timeout: int = 60,
    safe_mode: bool = True,
    lang: str = "zh",
    prompt: str = "",
    auto_mode: bool = False,
):
    set_lang(lang)

    profile = load_profile()
    agent_name, user_name = _setup_identity(profile)

    provider = create_provider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        tools_enabled=True,
    )

    from .tools import subagent as _subagent
    _subagent.init(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
    )

    from . import plugin_manager
    plugin_manager.discover()
    plugin_count = len(plugin_manager._plugins)
    if plugin_count:
        console.print(f"  [{GREEN}]Plugins: {plugin_count} loaded[/]")

    from .mcp_client import init_all as mcp_init
    mcp_errors = mcp_init()
    if mcp_errors:
        for e in mcp_errors:
            console.print(f"  [{ORANGE}]MCP: {e}[/]")

    tool_schemas = get_tool_schemas()
    system_prompt = build_system_prompt(lang, safe_mode, tool_schemas, profile)

    fluxlite_md = build_fluxlite_md()
    if fluxlite_md:
        system_prompt += f"\n\n## Project Context\n\n{fluxlite_md}"

    project_memory = build_project_memory()
    if project_memory:
        system_prompt += f"\n\n## Project Memory (persistent, project-specific knowledge)\n\n{project_memory}"

    instructions_md = build_instructions_md()
    if instructions_md:
        system_prompt += f"\n\n## User Instructions\n\n{instructions_md}"

    project_tree = build_project_tree()
    if project_tree:
        system_prompt += f"\n\n## Project Structure\n\n{project_tree}"

    git_context = build_git_context()
    if git_context:
        system_prompt += f"\n\n## Git State\n\n{git_context}"

    messages = [{"role": "system", "content": system_prompt}]

    git_branch = ""
    if git_context:
        for line in git_context.split("\n"):
            if line.startswith("Branch:"):
                git_branch = line[len("Branch:"):].strip()
                break

    context_extra = {
        "fluxlite_md": fluxlite_md,
        "instructions_md": instructions_md,
        "project_tree": project_tree,
        "git_context": git_context,
        "git_branch": git_branch,
        "agent_name": agent_name,
    }

    if prompt:
        messages.append({"role": "user", "content": prompt})

        if auto_mode:
            for _turn in range(10):
                result = _stream_response(provider, messages, tool_schemas, agent_name)
                content = result.get("content", "")
                tool_calls = result.get("tool_calls", [])
                truncated = result.get("truncated", False)

                if content:
                    sys.stdout.write(content)
                    sys.stdout.write("\n" if not content.endswith("\n") else "")

                if not tool_calls:
                    break

                openai_tool_calls = []
                tool_results = []
                for tc in tool_calls:
                    sys.stdout.write(f"\n[tool] {tc.name}\n")
                    r = execute_tool(tc.name, tc.arguments)
                    tool_results.append((tc, r))
                    openai_tool_calls.append({
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    })

                msg = {"role": "assistant", "content": content or "",
                       "tool_calls": openai_tool_calls}
                if result.get("reasoning"):
                    msg["reasoning_content"] = result["reasoning"]
                messages.append(msg)

                for tc, r in tool_results:
                    messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": r[:2000],
                    })

                if truncated:
                    break
        else:
            result = _stream_response(provider, messages, tool_schemas, agent_name)
            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])
            if content:
                sys.stdout.write(content)
                sys.stdout.write("\n" if not content.endswith("\n") else "")
            if tool_calls:
                names = [tc.name for tc in tool_calls]
                sys.stdout.write(f"\n[tool calls: {', '.join(names)} — use --auto to execute]\n")
        return

    session = _load_session()
    if session:
        messages.extend(session)
        msg_count = sum(1 for m in session if m.get("role") in ("user", "assistant"))
        console.print(f"  [{GRAY}]Loaded session ({msg_count} msgs) — /last to view[/]")

    console.print(f"  [{GRAY}]model: {model}     /help  /tools  /memory  /exit[/]")
    console.print(f"  [{GRAY}]{'='*45}[/]")

    while True:
        try:
            console.print(f"\n  [{CYAN}]{'─'*24} Input {'─'*24}[/]")
            user_input = read_input(f"  ")
        except EOFError:
            console.print()
            continue
        except KeyboardInterrupt:
            console.print()
            confirm = _ask_input(f"  [{ORANGE}]Exit? (y/N)[/] ")
            if confirm.strip().lower() in ("y", "yes"):
                _save_session(messages[1:])
                console.print(f"\n  [{DIM}]{_('exit')}[/]")
                break
            continue

        while user_input.endswith("\n"):
            user_input = user_input[:-1]
        user_input = user_input.rstrip()
        while user_input.endswith("\\"):
            user_input = user_input[:-1] + "\n"
            next_line = _ask_input("    ")
            user_input += next_line.rstrip()

        user_input = user_input.strip()
        if not user_input:
            if check_rewind_flag():
                if perform_rewind(messages):
                    console.print(f"  [{PURPLE}]{_('rewind_done')}[/]")
                    sys.stdout.write('\033[1A\033[J')
                    sys.stdout.flush()
            continue

        sys.stdout.write('\033[4A\033[J')
        sys.stdout.flush()

        if user_input.startswith("/"):
            should_exit = handle_command(user_input, messages, model, provider, context_extra)
            if CommandState.new_session_requested:
                CommandState.new_session_requested = False
                _save_session(messages[1:])
                messages[:] = [messages[0]]
                _reset_session()
                console.print(f"  [{CYAN}]New session started[/]")
            if CommandState.session_load_requested:
                CommandState.session_load_requested = False
                _save_session(messages[1:])
                messages[:] = [messages[0]]
                if CommandState.session_load_data:
                    messages.extend(CommandState.session_load_data)
                    for msg in CommandState.session_load_data:
                        role = msg["role"]
                        if role == "user":
                            _print_user(msg.get("content", ""))
                        elif role == "assistant":
                            content = msg.get("content", "")
                            if content:
                                ts = _now()
                                console.print(f"\n[{CYAN}]{agent_name}[/]  [{GRAY}]{ts}[/]")
                                console.print(Markdown(content, code_theme="monokai"))
                CommandState.session_load_data = None
                _reset_session()
                console.print(f"\n  [{CYAN}]Session loaded[/]")
            if should_exit:
                _save_session(messages[1:])
                break
            continue

        messages.append({"role": "user", "content": user_input})
        _print_user(user_input)

        turn = 0
        _has_file_changes = False
        while turn < 10:
            turn += 1

            result = _stream_response(provider, messages, tool_schemas, agent_name, max_retries=3)

            assistant_content = result.get("content", "")
            assistant_reasoning = result.get("reasoning", "")
            pending_tool_calls = result.get("tool_calls", [])
            last_usage = result.get("usage")
            received = result.get("received", False)
            truncated = result.get("truncated", False)
            if not received:
                console.print(f"\n  [{ORANGE}]! {_('error')}: AI returned empty response[/]")
                _save_session(messages[1:])
                break

            if CommandState.show_token_usage and last_usage:
                usage_str = ""
                if "prompt_tokens" in last_usage:
                    _cumulative_tokens["input"] += last_usage["prompt_tokens"]
                    usage_str += f"in: {last_usage['prompt_tokens']}  "
                elif "input_tokens" in last_usage:
                    _cumulative_tokens["input"] += last_usage["input_tokens"]
                    usage_str += f"in: {last_usage['input_tokens']}  "
                if "completion_tokens" in last_usage:
                    _cumulative_tokens["output"] += last_usage["completion_tokens"]
                    usage_str += f"out: {last_usage['completion_tokens']}  "
                elif "output_tokens" in last_usage:
                    _cumulative_tokens["output"] += last_usage["output_tokens"]
                    usage_str += f"out: {last_usage['output_tokens']}  "
                if usage_str:
                    total = _cumulative_tokens["input"] + _cumulative_tokens["output"]
                    max_tok = _get_max_tokens(model)
                    bar = _render_progress_bar(total, max_tok)
                    console.print(f"  [{DIM}]\u2502 {usage_str}[/]")
                    console.print(f"  [{DIM}]\u2502 {_('cumulative')}: in {_cumulative_tokens['input']} + out {_cumulative_tokens['output']}[/]  [{CYAN}]{bar}[/]")
                    if total > max_tok * 0.8:
                        console.print(f"  [{ORANGE}]! ctx ~{total}/{max_tok} \u2014 /truncate or /rewind advised[/]")
                    if total > max_tok * 0.88:
                        _auto_compress(messages, max_tok)

            if not pending_tool_calls:
                if assistant_content:
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

            if assistant_content:
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

            _tool_group: list = []

            def _display_width(s):
                return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)

            def _fmt_args(s, prefix_w=0):
                term_w = shutil.get_terminal_size().columns
                avail = term_w - prefix_w - 3
                if avail < 10:
                    avail = 80
                return s if _display_width(s) <= avail else s[:avail-3] + "..."

            def _flush_tool_group():
                if not _tool_group:
                    return
                name = _tool_group[0][0]
                count = len(_tool_group)

                if count == 1:
                    _, args_str, result, qlines = _tool_group[0]
                    console.print(f"\n  [{ORANGE}]{name}[/]")
                    console.print(f"  ⎿  {_fmt_args(args_str, 5)}")
                    if CommandState.show_tool_result:
                        console.print(Text(result[:2000], style=Style(color=GRAY_LIGHT)))
                    for line in qlines:
                        console.print(f"  [{ORANGE}]  {line}[/]")
                else:
                    console.print(f"\n  [{ORANGE}]{name} x {count}[/]")
                    for i, (_, args_str, result, qlines) in enumerate(_tool_group):
                        console.print(f"  ⎿  [{i+1}] {_fmt_args(args_str, 10)}")
                        for line in qlines:
                            console.print(f"  [{ORANGE}]     {line}[/]")
                    if CommandState.show_tool_result:
                        _, _, r1, _ = _tool_group[0]
                        console.print(f"  ⎿  [1] result: {r1[:150]}[/]")
                        if count > 1:
                            _, _, rn, _ = _tool_group[-1]
                            console.print(f"  ⎿  [{count}] result: {rn[:150]}[/]")
                _tool_group.clear()

            for tc in pending_tool_calls:
                args_str = ", ".join(f"{k}={v}" for k, v in tc.arguments.items())

                if _tool_group and _tool_group[0][0] != tc.name:
                    _flush_tool_group()

                if safe_mode:
                    confirm = _confirm_tool(tc.name, tc.arguments)
                    if confirm == "skip":
                        continue
                    if confirm == "deny":
                        _flush_tool_group()
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": "[cancelled] Operation cancelled by user",
                        })
                        console.print(f"\n  [{ORANGE}]{tc.name}[/]  [{RED}]cancelled[/]")
                        continue
                s = _Spinner()
                s.start(_("processing"))
                try:
                    result = execute_tool(tc.name, tc.arguments)
                finally:
                    s.stop()

                quality_lines = []

                if tc.name in ("file_write", "file_edit", "file_append"):
                    fpath = tc.arguments.get("path", "")
                    if fpath:
                        qe = _quality_gate(fpath)
                        if qe:
                            quality_lines.append(qe)
                            result = f"{result}\n\n{qe}"
                            choice = radio_select(f"Auto-fix {Path(fpath).name}?", [
                                ("fix", "Fix with AI"),
                                ("skip", "Skip (AI will see error)"),
                            ])
                            if choice == "fix":
                                fixed = _auto_fix_file(fpath, qe, provider)
                                if fixed:
                                    Path(fpath).write_text(fixed, encoding="utf-8")
                                    recheck = _quality_gate(fpath)
                                    if recheck:
                                        quality_lines.append(f"Fix failed: {recheck}")
                                        result += f"\n\n[auto-fix FAILED]: {recheck}"
                                    else:
                                        quality_lines.append("✓ File fixed")
                                        result += "\n\n[auto-fix OK]"
                                else:
                                    quality_lines.append("Auto-fix skipped (LLM error)")

                _tool_group.append((tc.name, args_str, result, quality_lines))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

                if CommandState.git_autocommit and tc.name in (
                    "file_write", "file_edit", "file_append", "file_delete",
                ):
                    _has_file_changes = True

            if _tool_group:
                _flush_tool_group()

            pending_tool_calls = []

        if turn >= 10:
            console.print(f"  [{ORANGE}]Max turns reached[/]")

        if CommandState.git_autocommit and _has_file_changes:
            try:
                msg = f"fluxlite: AI {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                subprocess.run(
                    ["git", "add", "-A"],
                    capture_output=True, text=True, timeout=10,
                )
                r = subprocess.run(
                    ["git", "commit", "-m", msg],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0:
                    short = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else "committed"
                    console.print(f"  [{GREEN}]\\u2713 {short}[/]")
            except (subprocess.TimeoutExpired, OSError, PermissionError):
                pass
