import json
from datetime import datetime
from pathlib import Path

from .i18n import _, set_lang
from .styles import CYAN, GREEN, PURPLE, ORANGE, RED, GRAY, DIM
from .provider import detect_provider_type
from .tools.registry import TOOLS
from .memory import load_memory
from .console import console, get_input


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
    memory = load_memory()
    identity = memory.get("identity", {})
    console.print(f"\n  [{CYAN}]Identity[/]")
    if identity.get("name"):
        console.print(f"    Name: {identity['name']}")
    if identity.get("user_name"):
        console.print(f"    User: {identity['user_name']}")
    if identity.get("personality"):
        console.print(f"    Personality: {identity['personality']}")

    rules = memory.get("rules", [])
    if rules:
        console.print(f"\n  [{ORANGE}]Rules ({len(rules)})[/]")
        for i, r in enumerate(rules):
            console.print(f"    {i+1}. {r}")
    else:
        console.print(f"\n  [{GRAY}]No rules set[/]")

    memories = memory.get("memories", [])
    if memories:
        console.print(f"\n  [{PURPLE}]Memories ({len(memories)})[/]")
        for m in memories[-5:]:
            console.print(f"    {m.get('content', '')[:80]}")
    console.print()


def compact_memory():
    memory = load_memory()
    entries = memory.get("memories", [])
    if len(entries) < 3:
        console.print(f"  [{GRAY}]Memory is already compact ({len(entries)} entries)[/]")
        return
    from .memory import save_memory
    summary = "\n".join(f"- {e['content']}" for e in entries)
    memory["memories"] = [
        {"id": "compact", "content": f"Consolidated memory:\n{summary}", "created_at": datetime.now().isoformat()}
    ]
    save_memory(memory)
    console.print(f"  [{PURPLE}]{_('compact_done')} ({len(entries)} entries compacted)[/]")


class CommandState:
    thinking_mode = "off"
    show_tool_result = False
    show_token_usage = False


def handle_command(cmd: str, messages: list, model: str, provider):
    state = CommandState
    cmd = cmd.lower().strip()

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
        console.print(f"    [{GREEN}]/rule <text>[/]  {_('rule_desc')}")
        console.print(f"    [{GREEN}]/tools[/]        {_('tools_desc')}")
        console.print(f"    [{GREEN}]/lang[/]         {_('lang_desc')}")
        console.print(f"    [{GREEN}]/exit[/]         {_('exit_desc')}")
        return False

    if cmd == "/clear":
        console.clear()
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

    if cmd in ("/exit", "/quit"):
        console.print(f"\n  [{DIM}]{_('exit')}[/]")
        return True

    if cmd == "/tools":
        console.print()
        console.print(f"  [{ORANGE}]\u2501 Tools ({len(TOOLS)})[/]")
        for t in TOOLS:
            params = ", ".join(t.parameters.keys()) if t.parameters else ""
            console.print(f"    [{GREEN}]{t.name}[/]({params})  [{GRAY}]{t.description[:50]}[/]")
        return False

    if cmd == "/memory":
        show_memory()
        return False

    if cmd == "/compact":
        compact_memory()
        return False

    if cmd == "/truncate":
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "assistant":
                messages.pop(i)
                console.print(f"  [{ORANGE}]! {_('truncated')}[/]")
                break
        return False

    if cmd.startswith("/rule "):
        rule = cmd[6:].strip()
        if rule:
            memory = load_memory()
            from .memory import add_rule
            add_rule(memory, rule)
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

    console.print(f"  [{RED}]x unknown: {cmd}[/]")
    return False
