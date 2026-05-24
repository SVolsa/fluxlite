import difflib
import json
import os
import shlex
from datetime import datetime
from pathlib import Path

from .i18n import _, set_lang
from .styles import CYAN, GREEN, PURPLE, ORANGE, RED, GRAY, DIM, BLUE
from .provider import detect_provider_type
from .tools.registry import TOOLS
from .profile import load_profile, save_profile, add_rule as profile_add_rule
from .startup import print_header
from .memory import load_memories, save_memories
from .console import console, get_input, radio_select


MODEL_PRESETS = {
    "deepseek": [
        ("1", "DeepSeek V4 Flash", "deepseek-v4-flash"),
        ("2", "DeepSeek V4 Pro", "deepseek-v4-pro"),
        ("3", "DeepSeek Chat", "deepseek-chat"),
        ("4", "DeepSeek Reasoner", "deepseek-reasoner"),
    ],
    "openai": [
        ("1", "GPT-4o", "gpt-4o"),
        ("2", "GPT-4o Mini", "gpt-4o-mini"),
        ("3", "GPT-4 Turbo", "gpt-4-turbo"),
        ("4", "GPT-3.5 Turbo", "gpt-3.5-turbo"),
    ],
    "openrouter": [
        ("1", "OpenAI GPT-4o", "openai/gpt-4o"),
        ("2", "Claude 3.5 Sonnet", "anthropic/claude-3.5-sonnet"),
        ("3", "Gemini 2.0 Flash", "google/gemini-2.0-flash"),
        ("4", "DeepSeek V4", "deepseek/deepseek-chat"),
    ],
    "groq": [
        ("1", "Llama 3.3 70B", "llama-3.3-70b-versatile"),
        ("2", "Mixtral 8x7B", "mixtral-8x7b-32768"),
        ("3", "Gemma2 9B", "gemma2-9b-it"),
    ],
    "anthropic": [
        ("1", "Claude Sonnet 4", "claude-sonnet-4-20250514"),
        ("2", "Claude Haiku 3.5", "claude-3-5-haiku-latest"),
        ("3", "Claude Opus 4", "claude-opus-4-20250514"),
    ],
}


def show_memory():
    profile = load_profile()
    identity = profile.get("identity", {})
    console.print(f"\n  [{CYAN}]Identity[/]")
    if identity.get("name"):
        console.print(f"    Name: {identity['name']}")
    if identity.get("user_name"):
        console.print(f"    User: {identity['user_name']}")
    if identity.get("personality"):
        console.print(f"    Personality: {identity['personality']}")

    rules = profile.get("rules", [])
    if rules:
        console.print(f"\n  [{ORANGE}]Rules ({len(rules)})[/]")
        for i, r in enumerate(rules):
            console.print(f"    {i+1}. {r}")
    else:
        console.print(f"\n  [{GRAY}]No rules set[/]")

    entries = load_memories()
    if entries:
        console.print(f"\n  [{PURPLE}]Memories ({len(entries)})[/]")
        for m in entries[-5:]:
            console.print(f"    {m.get('content', '')[:80]}")
    console.print()


def compact_memory():
    entries = load_memories()
    if len(entries) < 3:
        console.print(f"  [{GRAY}]Memory is already compact ({len(entries)} entries)[/]")
        return
    summary = "\n".join(f"- {e['content']}" for e in entries)
    compacted = {
        "id": "compact",
        "content": f"Consolidated memory:\n{summary}",
        "created_at": datetime.now().isoformat(),
    }
    save_memories([compacted])
    console.print(f"  [{PURPLE}]{_('compact_done')} ({len(entries)} entries compacted)[/]")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        pass
    import unicodedata
    cjk = sum(1 for c in text if "CJK" in unicodedata.name(c, "") or
              "一" <= c <= "鿿" or "　" <= c <= "〿")
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    other = len(text) - cjk - ascii_chars
    return max(1, cjk * 2 + ascii_chars // 4 + other // 3)


def perform_rewind(messages: list) -> bool:
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            del messages[i:]
            return True
    return False


class CommandState:
    thinking_mode = "off"
    show_tool_result = False
    show_token_usage = False
    new_session_requested = False
    session_load_requested = False
    session_load_data = None
    git_autocommit = False
    pinned_files: set = set()

    @classmethod
    def reset_pins(cls):
        cls.pinned_files = set()


def handle_command(cmd: str, messages: list, model: str, provider, context_extra: dict = None):
    state = CommandState
    cmd = cmd.lower().strip()

    # Short aliases
    _aliases = {"/s": "/sessions", "/p": "/plan", "/c": "/compact", "/q": "/exit"}
    if cmd in _aliases:
        cmd = _aliases[cmd]

    if cmd in ("/help", "/h"):
        console.print()
        console.print(f"  [{CYAN}]\u2501 Commands[/]")
        console.print(f"    [{GREEN}]/help[/]         {_('help_desc')}")
        console.print(f"    [{GREEN}]/clear[/]        {_('clear_desc')}")
        console.print(f"    [{GREEN}]/model[/]        {_('model_desc')}")
        console.print(f"    [{GREEN}]/memory[/]       {_('show_memory')}")
        console.print(f"    [{GREEN}]/think[/]        {_('think_desc')}")
        console.print(f"    [{GREEN}]/compact[/]      {_('compact_desc')}")
        console.print(f"    [{GREEN}]/toolresult[/]   {_('toolresult_desc')}")
        console.print(f"    [{GREEN}]/export[/]       {_('export_desc')}")
        console.print(f"    [{GREEN}]/token[/]        {_('token_desc')}")
        console.print(f"    [{GREEN}]/truncate[/]     {_('truncate_desc')}")
        console.print(f"    [{GREEN}]/rewind[/]      {_('rewind_desc')}")
        console.print(f"    [{GREEN}]/context[/]     {_('context_desc')}")
        console.print(f"    [{GREEN}]/rule <text>[/]  {_('rule_desc')}")
        console.print(f"    [{GREEN}]/tools[/]        {_('tools_desc')}")
        console.print(f"    [{GREEN}]/lang[/]         {_('lang_desc')}")
        console.print(f"    [{GREEN}]/git[/]          Run git commands interactively")
        console.print(f"    [{GREEN}]/autocommit[/]   Toggle git auto-commit after AI file changes")
        console.print(f"    [{GREEN}]/exit[/]         {_('exit_desc')}")
        console.print(f"    [{GREEN}]/new[/]          {_('new_desc')}")
        console.print(f"    [{GREEN}]/sessions[/]     {_('sessions_desc')}")
        console.print(f"    [{GREEN}]/search[/]      Search session history by keyword")
        console.print(f"    [{GREEN}]/plan[/]        Plan and execute multi-step tasks autonomously")
        console.print(f"    [{GREEN}]/mcp[/]         Manage MCP servers (add/remove/list)")
        console.print(f"    [{GREEN}]/hooks[/]       List hook scripts in ~/.fluxlite/hooks/")
        console.print(f"    [{GREEN}]/plugin[/]     Manage plugins (list/info/enable/disable/create/reload)")
        console.print(f"    [{GREEN}]/sandbox[/]     Manage sandbox (on/off/review/apply/discard/status)")
        console.print(f"    [{GREEN}]/last[/]        Show current conversation history")
        console.print(f"    [{GREEN}]/init[/]        Generate FLUXLITE.md for this project")
        console.print(f"    [{GREEN}]/diff[/]        View uncommitted changes")
        console.print(f"    [{GREEN}]/review[/]      AI code review of staged changes")
        console.print(f"    [{GREEN}]/fix[/]         Auto-fix last lint/test error")
        console.print(f"    [{GREEN}]/pin <file>[/]  Pin files to protect from truncation")
        return False

    if cmd == "/last":
        _show_history(messages, context_extra)
        return False

    if cmd == "/clear":
        os.system("cls" if os.name == "nt" else "clear")
        print_header(model=model)
        console.print()
        return False

    if cmd.startswith("/model"):
        provider_key = detect_provider_type(provider._client.base_url)
        presets = MODEL_PRESETS.get(provider_key, [])
        if presets:
            console.print()
            console.print(f"  [{CYAN}]\u2501 Available Models[/]")
            for key, label, name in presets:
                marker = "[bold]" if name == provider.model else ""
                console.print(f"    [{GREEN}]{key}[/]) {marker}{label}[/]")
            console.print(f"    [custom] Custom input")
        choice = get_input(f"  Select model: ")
        choice = choice.strip()
        if choice == "custom":
            new_model = get_input(f"  Model name: ")
            if new_model.strip():
                provider.model = new_model.strip()
                console.print(f"  [{PURPLE}]model: {provider.model}[/]")
        elif choice and presets:
            for key, label, name in presets:
                if choice == key:
                    provider.model = name
                    console.print(f"  [{PURPLE}]model: {label} ({name})[/]")
                    break
        return False

    if cmd == "/lang":
        choice = get_input(f"  lang (1=zh, 2=en): ")
        choice = choice.strip()
        if choice in ("1", "zh"):
            set_lang("zh")
            console.print(f"  [{CYAN}]lang: zh[/]")
        elif choice in ("2", "en"):
            set_lang("en")
            console.print(f"  [{CYAN}]lang: en[/]")
        return False

    if cmd == "/new":
        state.new_session_requested = True
        console.print(f"  [{GREEN}]New session[/]")
        return False

    if cmd == "/sessions":
        _handle_sessions()
        return False

    if cmd in ("/exit", "/quit"):
        console.print(f"\n  [{DIM}]{_('exit')}[/]")
        return True

    if cmd == "/tools":
        console.print()
        console.print(f"  [{ORANGE}]\u2501 Tools ({len(TOOLS)})[/]")
        for t in TOOLS:
            params = ", ".join(t.parameters.keys()) if t.parameters else ""
            console.print(f"    [{GREEN}]{t.name}[/]({params})  [{GRAY}]{_(t.description)[:50]}[/]")
        return False

    if cmd == "/memory":
        show_memory()
        return False

    if cmd == "/compact":
        compact_memory()
        return False

    if cmd == "/truncate":
        removed = False
        # 1) Remove oldest tool cycle (assistant with tool_calls + tool results)
        for i in range(1, len(messages)):
            if messages[i].get("tool_calls"):
                del messages[i]
                while i < len(messages) and messages[i]["role"] == "tool":
                    del messages[i]
                console.print(f"  [{ORANGE}]! {_('truncate_smart')}[/]")
                removed = True
                break
        # 2) Fallback: remove oldest user+assistant exchange
        if not removed:
            for i in range(1, len(messages) - 1):
                if messages[i]["role"] == "user":
                    del messages[i:i+2]
                    console.print(f"  [{ORANGE}]! {_('truncate_exchange')}[/]")
                    removed = True
                    break
        if not removed:
            console.print(f"  [{GRAY}]Nothing to truncate[/]")
        return False

    if cmd.startswith("/rule "):
        rule = cmd[6:].strip()
        if rule:
            profile = load_profile()
            profile_add_rule(profile, rule)
            console.print(f"  [{GREEN}]Rule recorded: {rule}[/]")
        return False

    if cmd.startswith("/toolresult"):
        parts = cmd.split()
        if len(parts) >= 2:
            if parts[1] == "on":
                state.show_tool_result = True
                console.print(f"  [{PURPLE}]Tool result display: on[/]")
            elif parts[1] == "off":
                state.show_tool_result = False
                console.print(f"  [{GRAY}]Tool result display: off[/]")
        return False

    if cmd == "/export":
        export_path = Path.cwd() / f"fluxlite-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(f"# FluxLite Conversation Export\n\n")
                for m in messages:
                    role = m.get("role", "")
                    content = m.get("content", "")
                    if role == "system":
                        continue
                    elif role == "user":
                        f.write(f"## User\n\n{content}\n\n")
                    elif role == "assistant":
                        f.write(f"## Assistant\n\n{content}\n\n")
                    elif role == "tool":
                        f.write(f"> Tool result: {content[:200]}\n\n")
            console.print(f"  [{GREEN}]Exported to: {export_path}[/]")
        except Exception as e:
            console.print(f"  [{RED}]Export failed: {e}[/]")
        return False

    if cmd == "/token":
        state.show_token_usage = not state.show_token_usage
        status = "on" if state.show_token_usage else "off"
        console.print(f"  [{'PURPLE' if state.show_token_usage else 'GRAY'}]Token usage display: {status}[/]")
        return False

    if cmd.startswith("/think"):
        parts = cmd.split()
        if len(parts) >= 2:
            sub = parts[1]
            if sub == "on":
                state.thinking_mode = "visible"
                console.print(f"  [{PURPLE}]{_('think_on')}[/]")
            elif sub == "off":
                state.thinking_mode = "off"
                console.print(f"  [{GRAY}]{_('think_off')}[/]")
            elif sub == "display":
                if len(parts) >= 3 and parts[2] == "off":
                    state.thinking_mode = "collapsed"
                    console.print(f"  [{GRAY}]{_('think_display_off')}[/]")
                else:
                    state.thinking_mode = "visible"
                    console.print(f"  [{PURPLE}]{_('think_display_on')}[/]")
        return False

    if cmd == "/autocommit":
        state.git_autocommit = not state.git_autocommit
        status = "on" if state.git_autocommit else "off"
        console.print(f"  [{'PURPLE' if state.git_autocommit else 'GRAY'}]Git auto-commit: {status}[/]")
        return False

    if cmd.startswith("/search"):
        keyword = cmd[8:].strip()
        if keyword:
            _handle_search(keyword)
        else:
            keyword = get_input(f"  Search keyword: ").strip()
            if keyword:
                _handle_search(keyword)
        return False

    if cmd == "/git":
        _handle_git()
        return False

    if cmd.startswith("/plan"):
        _handle_plan(cmd[6:].strip(), messages)
        return False

    if cmd == "/mcp":
        _handle_mcp()
        return False

    if cmd == "/hooks":
        from .tools.hooks import list_hooks
        console.print(list_hooks())
        return False

    if cmd.startswith("/plugin"):
        from . import plugin_manager
        parts = cmd.split()
        if len(parts) < 2:
            console.print(f"  Usage: /plugin <list|info|enable|disable|create|reload>")
            return False
        sub = parts[1]

        if sub == "list":
            console.print(plugin_manager.list_plugins())
        elif sub == "reload":
            console.print(plugin_manager.reload_plugins())
        elif sub == "info" and len(parts) >= 3:
            console.print(plugin_manager.plugin_info(parts[2]))
        elif sub == "enable" and len(parts) >= 3:
            console.print(plugin_manager.enable_plugin(parts[2]))
        elif sub == "disable" and len(parts) >= 3:
            console.print(plugin_manager.disable_plugin(parts[2]))
        elif sub == "create" and len(parts) >= 3:
            console.print(plugin_manager.create_plugin(parts[2]))
        else:
            console.print(f"  Usage: /plugin <list|info|enable|disable|create|reload>")
        return False

    if cmd.startswith("/sandbox"):
        from .tools.sandbox import _SandboxState
        parts = cmd.split()
        if len(parts) < 2:
            console.print(f"  Usage: /sandbox <on|off|review|apply|discard|status>")
            return False
        sub = parts[1]
        if sub == "on":
            path = _SandboxState.enable()
            console.print(f"  [purple]Sandbox: enabled[/]  [gray]temp: {path}[/]")
        elif sub == "off":
            _SandboxState.disable()
            console.print(f"  [gray]Sandbox: disabled[/]")
        elif sub == "status":
            console.print(f"  [cyan]{_SandboxState.status()}[/]")
        elif sub == "review":
            diff = _SandboxState.review()
            console.print(diff if diff else "  [gray]No pending changes[/]")
        elif sub == "apply":
            msg = _SandboxState.apply()
            console.print(f"  [green]{msg}[/]")
        elif sub == "discard":
            msg = _SandboxState.discard()
            console.print(f"  [orange]{msg}[/]")
        else:
            console.print(f"  [red]Unknown subcommand: {sub} (use on/off/review/apply/discard/status)[/]")
        return False

    if cmd == "/init":
        from .context import generate_fluxlite_md
        generate_fluxlite_md(console, radio_select)
        return False

    if cmd == "/context":
        parts = cmd.split()
        if len(parts) > 1 and parts[1] == "system":
            sys_content = messages[0].get("content", "") if messages else ""
            if sys_content:
                from rich.markdown import Markdown
                console.print(f"\n  [{CYAN}]━━━ System Prompt ({len(sys_content)} chars) ━━━[/]")
                console.print(f"  [{GRAY}]{sys_content[:3000]}[/]")
                if len(sys_content) > 3000:
                    console.print(f"  [{GRAY}]... ({len(sys_content) - 3000} more chars)[/]")
                console.print()
            else:
                console.print(f"  [{GRAY}]No system prompt[/]")
        else:
            _show_context(messages, model, context_extra or {})
        return False

    if cmd.startswith("/pin"):
        parts = cmd.split()
        if len(parts) >= 2:
            f = parts[1]
            if f in CommandState.pinned_files:
                CommandState.pinned_files.discard(f)
                console.print(f"  [{GRAY}]Unpinned: {f}[/]")
            else:
                CommandState.pinned_files.add(f)
                console.print(f"  [{GREEN}]Pinned: {f}[/]")
        else:
            if CommandState.pinned_files:
                console.print(f"  [{CYAN}]Pinned files:[/]")
                for f in sorted(CommandState.pinned_files):
                    console.print(f"    [{GRAY}]{f}[/]")
            else:
                console.print(f"  [{GRAY}]No pinned files[/]")
        return False

    if cmd == "/diff":
        import subprocess
        try:
            r = subprocess.run(
                ["git", "diff"], capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
            out = r.stdout.strip() if r.stdout else ""
            if out:
                console.print(f"  [{CYAN}]━━━ git diff ━━━[/]")
                for line in out.split("\n")[:80]:
                    console.print(f"  [{GRAY}]{line[:100]}[/]")
                if out.count("\n") > 80:
                    console.print(f"  [{GRAY}]... ({out.count(chr(10)) - 80} more lines)[/]")
            else:
                console.print(f"  [{GRAY}]No changes[/]")
        except Exception as e:
            console.print(f"  [{RED}]{e}[/]")
        return False

    if cmd == "/review":
        import subprocess
        try:
            r = subprocess.run(
                ["git", "diff", "--cached"], capture_output=True, text=True,
                timeout=10, encoding="utf-8", errors="replace",
            )
            diff = r.stdout.strip() if r.stdout else ""
            if not diff:
                r2 = subprocess.run(
                    ["git", "diff"], capture_output=True, text=True, timeout=10,
                    encoding="utf-8", errors="replace",
                )
                diff = (r2.stdout or "").strip()
            if not diff:
                console.print(f"  [{GRAY}]No changes to review[/]")
                return False
        except Exception as e:
            console.print(f"  [{RED}]{e}[/]")
            return False

        review_prompt = (
            "Review the following code changes. "
            "Identify bugs, style issues, logic errors, and suggest improvements.\n\n"
            f"```diff\n{diff[:4000]}\n```"
        )
        messages.append({"role": "user", "content": review_prompt})
        console.print(f"  [{GREEN}]Review requested ({len(diff)} chars of diff)[/]")
        return False

    if cmd == "/fix":
        # Find last error in conversation
        last_error = ""
        for m in reversed(messages):
            c = m.get("content", "")
            if "error" in c.lower() or "traceback" in c.lower() or "FAIL" in c:
                last_error = c
                break
        if not last_error:
            console.print(f"  [{GRAY}]No recent error found in conversation[/]")
            return False

        fix_prompt = (
            "The following error occurred. Please analyze it and fix the code.\n\n"
            f"Error:\n```\n{last_error[:2000]}\n```"
        )
        messages.append({"role": "user", "content": fix_prompt})
        console.print(f"  [{GRAY}]Analysis request sent[/]")
        return False

    if cmd == "/rewind":
        if perform_rewind(messages):
            console.print(f"  [{PURPLE}]{_('rewind_done')}[/]")
        else:
            console.print(f"  [{GRAY}]Nothing to rewind[/]")
        return False

    # Suggest closest known command
    known = ["help", "clear", "model", "memory", "think", "compact", "toolresult",
             "export", "token", "truncate", "rewind", "context", "tools", "lang",
             "git", "autocommit", "new", "sessions", "search", "last", "plan",
             "mcp", "hooks", "plugin", "sandbox", "exit", "rule",
             "diff", "review", "fix", "pin", "init"]
    cmd_name = cmd.lstrip("/")
    matches = difflib.get_close_matches(cmd_name, known, n=1, cutoff=0.5)
    if matches:
        console.print(f"  [{RED}]x unknown: {cmd}[/]  [{GRAY}]did you mean /{matches[0]}?[/]")
    else:
        console.print(f"  [{RED}]x unknown: {cmd}[/]")
    return False


def _show_context(messages: list, model: str, extra: dict):
    """Display current context information."""
    ctx = extra or {}

    # Message counts by role
    counts = {}
    for m in messages:
        role = m["role"]
        counts[role] = counts.get(role, 0) + 1
    total_msgs = len(messages)

    # Token estimates
    sys_prompt = messages[0].get("content", "") if messages else ""
    all_content = " ".join(
        m.get("content", "") for m in messages[1:]
    )
    sys_tokens = estimate_tokens(sys_prompt)
    total_tokens = sys_tokens + estimate_tokens(all_content)

    console.print()
    console.print(f"  [{CYAN}]━ {_('context_title')}[/]")
    console.print(f"    Model:        [{PURPLE}]{model}[/]")
    console.print(f"    {_('msg_count')}:      {total_msgs} {' '.join(f'({r}: {c})' for r, c in counts.items())}")
    console.print(f"    {_('system_size')}: ~{sys_tokens} {_('token_estimate')}")
    console.print(f"    {_('token_estimate')}:  ~{total_tokens} tokens ({sys_tokens} sys + {total_tokens - sys_tokens} chat)")

    fluxlite_md = extra.get("fluxlite_md", "")
    if fluxlite_md:
        md_len = len(fluxlite_md)
        md_tokens = estimate_tokens(fluxlite_md)
        console.print(f"    {_('project_ctx')}: FLUXLITE.md ({md_len} chars, ~{md_tokens} tokens)")
    else:
        console.print(f"    {_('project_ctx')}: [{GRAY}]FLUXLITE.md not loaded[/]")

    instructions = extra.get("instructions_md", "")
    if instructions:
        ins_len = len(instructions)
        ins_tokens = estimate_tokens(instructions)
        console.print(f"    Instructions:  INSTRUCTIONS.md ({ins_len} chars, ~{ins_tokens} tokens)")
    else:
        console.print(f"    Instructions:  [{GRAY}]not loaded[/]")

    tree = extra.get("project_tree", "")
    if tree:
        tree_lines = tree.count("\n") + 1
        console.print(f"    Project tree:  {tree_lines} lines")
    else:
        console.print(f"    Project tree:  [{GRAY}]not generated[/]")

    git = extra.get("git_context", "")
    if git:
        lines = git.count("\n") + 1
        branch = extra.get("git_branch", "?")
        console.print(f"    {_('git_state')}:     branch: {branch} ({lines} lines)")
    else:
        console.print(f"    {_('git_state')}:     [{GRAY}]no git repo[/]")
    console.print()


def _handle_git():
    """Run git commands interactively."""
    import subprocess
    cmd = get_input(f"  git ")
    if not cmd.strip():
        return
    try:
        r = subprocess.run(
            ["git"] + shlex.split(cmd),
            capture_output=True, text=True, timeout=30,
        )
        if r.stdout:
            console.print(f"  [{DIM}]{r.stdout.rstrip()}[/]")
        if r.stderr:
            console.print(f"  [{ORANGE}]{r.stderr.rstrip()}[/]")
        if r.returncode != 0 and not r.stderr:
            console.print(f"  [{RED}]exit code: {r.returncode}[/]")
    except FileNotFoundError:
        console.print(f"  [{RED}]git not found[/]")
    except Exception as e:
        console.print(f"  [{RED}]{e}[/]")


def _handle_plan(task: str, messages: list):
    """Start a planning session for a multi-step task."""
    if not task:
        console.print(f"  [{ORANGE}]Usage: /plan <task description>[/]")
        console.print(f"  [{GRAY}]Example: /plan refactor the user module with tests[/]")
        return

    from .mcp_client import init_all
    init_all()

    console.print(f"\n  [{PURPLE}]Planning mode:[/] {task}")
    console.print(f"  [{GRAY}]I will break this down and complete each step.[/]")

    plan_prompt = (
        f"You are now in PLAN mode. Task: {task}\n\n"
        "First, analyze the task and break it into numbered steps.\n"
        "Output the plan first, then execute each one at a time.\n"
        "After each step, verify it works (run tests, check syntax).\n"
        "Track progress. Report what was done."
    )
    messages.append({"role": "user", "content": f"/plan {task}\n\n{plan_prompt}"})
    console.print(f"  [{GREEN}]Plan started. AI will plan and execute step by step.[/]")


def _handle_mcp():
    """Manage MCP servers with radio_select."""
    from .mcp_client import (
        load_config, save_config, init_all, stop_all,
        stop_server, get_server_names, get_tool_list,
    )

    actions = [
        ("list", "List connected servers & tools"),
        ("add", "Add a new MCP server"),
        ("remove", "Remove an MCP server"),
        ("restart", "Restart all MCP servers"),
    ]
    act = radio_select("MCP Manager", actions)
    if not act:
        return

    if act == "list":
        servers = get_server_names()
        tools = get_tool_list()
        if not servers:
            console.print(f"  [{GRAY}]No MCP servers running.[/]")
            console.print(f"  [{GRAY}]Configure in ~/.fluxlite/mcp.json[/]")
        else:
            console.print(f"\n  [{CYAN}]MCP Servers ({len(servers)})[/]")
            for s in servers:
                console.print(f"    [{GREEN}]●[/] {s}")
            if tools:
                console.print(f"\n  [{PURPLE}]Tools ({len(tools)})[/]")
                for t in tools:
                    n, d = t.get("name", "?"), t.get("description", "")[:60]
                    console.print(f"    [{GREEN}]{n}[/]  [{GRAY}]{d}[/]")
        console.print()

    elif act == "add":
        name = get_input(f"  Server name: ").strip()
        if not name:
            return
        cmd = get_input(f"  Command (e.g. node, python): ").strip()
        if not cmd:
            return
        args_str = get_input(f"  Arguments (space-separated): ").strip()
        args = args_str.split() if args_str else []
        env_str = get_input(f"  Env vars (KEY=val, optional): ").strip()
        env = {}
        if env_str:
            for pair in env_str.split():
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    env[k] = v

        servers = load_config()
        servers.append({"name": name, "command": cmd, "args": args, "env": env})
        save_config(servers)
        err = init_all()
        console.print(f"  [{GREEN}]Added: {name}[/]")
        if err:
            for e in err:
                console.print(f"  [{ORANGE}]{e}[/]")

    elif act == "remove":
        servers = load_config()
        if not servers:
            return
        items = [(str(i + 1), s.get("name", "?")) for i, s in enumerate(servers)]
        pick = radio_select("Remove MCP server", items)
        if not pick:
            return
        idx = int(pick) - 1
        name = servers.pop(idx).get("name", "")
        save_config(servers)
        stop_server(name)
        console.print(f"  [{GREEN}]Removed: {name}[/]")

    elif act == "restart":
        stop_all()
        errs = init_all()
        if errs:
            for e in errs:
                console.print(f"  [{ORANGE}]{e}[/]")
        else:
            console.print(f"  [{GREEN}]MCP servers restarted[/]")


def _handle_search(keyword: str):
    """Search session history for keyword, present results with radio_select."""
    sessions_dir = Path.home() / ".fluxlite" / "history"
    if not sessions_dir.exists():
        console.print(f"  [{GRAY}]No saved sessions[/]")
        return

    files = sorted(sessions_dir.glob("*.json"), reverse=True)
    matches = []
    items = []
    kw_lower = keyword.lower()

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for msg in data:
            content = msg.get("content", "")
            if kw_lower in content.lower():
                ts = f.stem[:15] if len(f.stem) >= 15 else f.stem
                snippet = content.strip()[:80].replace("\n", " ")
                matches.append((data, f))
                items.append((str(len(matches)), f"{ts}  \"{snippet}\""))
                break  # one entry per file

    if not matches:
        console.print(f"  [{GRAY}]No sessions match \"{keyword}\"[/]")
        return

    console.print(f"  [{CYAN}]Found {len(matches)} session(s) matching \"{keyword}\"[/]")
    pick = radio_select(f"Search: {keyword}", items)
    if not pick:
        return

    data, path = matches[int(pick) - 1]
    actions = [
        ("load", "Load this session"),
        ("delete", "Delete"),
    ]
    act = radio_select(f"Session: {path.stem[:20]} — {len(data)} msgs", actions)

    if act == "load":
        CommandState.session_load_requested = True
        CommandState.session_load_data = data
        console.print(f"  [{PURPLE}]Switching session...[/]")
    elif act == "delete":
        path.unlink()
        console.print(f"  [{GREEN}]Session deleted[/]")


def _show_history(messages, context_extra):
    """Print current conversation history (user + assistant messages)."""
    from rich.markdown import Markdown
    from .styles import CYAN, GRAY

    agent_name = (context_extra or {}).get("agent_name", "FluxLite")
    user_msgs = [m for m in messages if m.get("role") in ("user", "assistant")]
    if not user_msgs:
        console.print(f"  [{GRAY}]No conversation yet[/]")
        return

    console.print(f"  [{GRAY}]── Conversation ({len(user_msgs)} msgs) ──[/]")
    for msg in user_msgs:
        role = msg["role"]
        content = msg.get("content", "")
        if role == "user":
            console.print(f"  [{GREEN}]>> {content[:200]}[/]")
        elif role == "assistant":
            if content:
                console.print(f"  [{CYAN}]{agent_name}:[/]")
                console.print(Markdown(content[:500], code_theme="monokai"))
    console.print(f"  [{GRAY}]{'─'*45}[/]")


def _generate_fluxlite_md():

    """浏览和管理历史会话（全屏弹出框 + 黑底主题）。"""
    sessions_dir = Path.home() / ".fluxlite" / "history"
    if not sessions_dir.exists():
        console.print(f"  [{GRAY}]No saved sessions[/]")
        return

    files = sorted(sessions_dir.glob("*.json"))
    if not files:
        console.print(f"  [{GRAY}]No saved sessions[/]")
        return

    # 构建会话列表 + 缓存数据
    sessions_cache = {}
    items = []
    for i, f in enumerate(files, 1):
        key = str(i)
        try:
            data = json.loads(f.read_text())
            sessions_cache[key] = (data, f)
            count = len(data)
        except Exception:
            sessions_cache[key] = ([], f)
            count = 0
        ts = f.stem
        if len(ts) == 15:
            dt = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}  {ts[9:11]}:{ts[11:13]}"
        else:
            dt = ts
        items.append((key, f"{dt}  ({count} msgs)"))

    pick = radio_select("Sessions", items)
    if not pick:
        return

    data, path = sessions_cache.get(pick, ([], None))
    if path is None:
        return

    actions = [
        ("load", "Load this session"),
        ("delete", "Delete"),
    ]

    act = radio_select(f"Session: {path.stem[:20]} — {len(data)} msgs", actions)

    if act == "load":
        CommandState.session_load_requested = True
        CommandState.session_load_data = data
        console.print(f"  [{PURPLE}]Switching session...[/]")
    elif act == "delete":
        path.unlink()
        console.print(f"  [{GREEN}]Session deleted[/]")
