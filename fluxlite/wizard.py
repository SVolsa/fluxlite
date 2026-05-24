import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.columns import Columns

from .styles import CYAN, GREEN, PURPLE, ORANGE, RED, BLUE, YELLOW, DIM
from .config import CONFIG_PATH, CONFIG_DIR, save_config, load_config
from .i18n import _, set_lang

console = Console()

API_PRESETS = {
    "1": {"name": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "2": {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "3": {"name": "Anthropic Claude", "base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-20250514"},
    "4": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini"},
    "5": {"name": "Groq", "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    "6": {"name": "Custom (自定义/Custom)", "base_url": "", "model": ""},
}

try:
    import pyfiglet
    _figlet_logo = pyfiglet.figlet_format("FluxLite", font="ansi_shadow")
    WIZARD_LOGO = "\n" + "\n".join(
        f"  [bold cyan]{line}[/]" for line in _figlet_logo.rstrip("\n").split("\n")
    )
except ImportError:
    WIZARD_LOGO = "\n  [bold cyan]===== FluxLite v0.5.2 =====[/]\n"


def _section(title: str):
    console.print(f"\n[{CYAN}]\u2501 {title}[/]")


def _info(msg: str):
    console.print(f"  [{DIM}]{msg}[/]")


def _ok(msg: str):
    console.print(f"  [{GREEN}]\u2713 {msg}[/]")


def _warn(msg: str):
    console.print(f"  [{ORANGE}]! {msg}[/]")


def _prompt(msg: str, default: str = "", password: bool = False) -> str:
    kwargs = {}
    if default:
        kwargs["default"] = default
    if password:
        return Prompt.ask(f"  [{GREEN}]?[/] {msg}", password=True, **kwargs)
    return Prompt.ask(f"  [{GREEN}]?[/] {msg}", **kwargs)


def _confirm(msg: str, default: bool = True) -> bool:
    return Confirm.ask(f"  [{GREEN}]?[/] {msg}", default=default)


def _select(title: str, options: dict) -> str:
    console.print(f"\n  [{GREEN}]?[/] {title}")
    for key, opt in options.items():
        name = opt.get("name", opt) if isinstance(opt, dict) else opt
        console.print(f"    [{CYAN}]{key}[/]) {name}")
    choice = Prompt.ask("  \u8f93\u5165\u7f16\u53f7", choices=list(options.keys()))
    return choice


def run_wizard():
    console.clear()
    console.print(WIZARD_LOGO)
    console.print(f"\n  [{CYAN}]fluxlite v1.0 - First-time setup (首次设置)[/]")
    console.print(f"  [{DIM}]Let's get you started in 2 minutes / 两分钟搞定[/]")

    _section("Language / 语言")
    lang_choice = _select("\u8bed\u8a00 Language", {
        "1": {"name": "\u4e2d\u6587 (Chinese)", "lang": "zh"},
        "2": {"name": "English", "lang": "en"},
    })
    lang = "zh" if lang_choice == "1" else "en"
    set_lang(lang)

    console.print(f"\n  [{GREEN}]\u2713 Language set to: {lang}[/]")

    _section(_("api_provider") if lang == "zh" else "API Provider")
    _info("Select your LLM provider / \u9009\u62e9 LLM \u670d\u52a1\u5546")

    api_choice = _select("Provider", API_PRESETS)
    preset = API_PRESETS[api_choice]

    base_url = preset["base_url"]
    default_model = preset["model"]

    if api_choice == "6":
        base_url = _prompt("API Base URL (e.g. https://api.deepseek.com)")
        default_model = _prompt("Default Model (e.g. deepseek-chat)")

    _section(_("api_key_setup") if lang == "zh" else "API Key")
    _info("Paste your API key / \u7c98\u8d34\u4f60\u7684 API Key")
    _info(f"  {base_url}")
    api_key = _prompt("API Key (输入API密钥)")

    if not api_key:
        _warn("API Key is required / API Key \u4e0d\u80fd\u4e3a\u7a7a")
        api_key = _prompt("API Key (输入API密钥)")

    _section("Model / \u6a21\u578b")
    model = _prompt("Model name", default=default_model)

    _section(_("test_connection") if lang == "zh" else "Test Connection")
    _info("Testing API connection...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10,
        )
        reply = resp.choices[0].message.content
        _ok(f"Connection OK! Response: {reply[:50]}")
    except Exception as e:
        _warn(f"Connection failed: {e}")
        _info("Config will still be saved, but check your API key and URL")
        if not _confirm("Continue anyway / \u7ee7\u7eed\u4fdd\u5b58? (y/n)"):
            return _ask_retry(lang, api_key, base_url, model, api_choice)

    _section("Web Search / \u7f51\u7edc\u641c\u7d22 (optional)")
    tavily_key = ""
    if _confirm("Setup web search (Tavily)? / \u8bbe\u7f6e\u7f51\u7edc\u641c\u7d22?", default=False):
        tavily_key = _prompt("Tavily API Key (get at https://tavily.com)")

    _section(_("saving") if lang == "zh" else "Save Configuration")
    config = {
        "api": {"key": api_key, "base_url": base_url, "model": model},
        "tavily": {"key": tavily_key},
        "app": {"language": lang, "max_turns": 100, "safe_mode": True, "timeout": 60},
        "tools": {"search_enabled": bool(tavily_key), "code_enabled": True, "file_enabled": True},
    }

    save_config(config)
    _ok(f"Config saved to {CONFIG_PATH}")

    console.print()
    console.print(Panel.fit(
        f"[{GREEN}]\u2713 FluxLite is ready!\n"
        f"  Model: {model}\n"
        f"  Search: {'enabled' if tavily_key else 'disabled'}\n"
        f"  Lang: {lang}[/]",
        border_style=CYAN,
    ))
    console.print(f"\n  [{DIM}]Run [bold]fluxlite[/] anytime to start chatting[/]")
    console.print()


def _ask_retry(lang, api_key, base_url, model, api_choice):
    if _confirm("Retry test? / \u91cd\u8bd5\u6d4b\u8bd5?"):
        pass


def run_wizard_if_needed():
    config = load_config()
    api_key = config.get("api", {}).get("key", "")
    if api_key:
        return config

    console.clear()
    console.print(WIZARD_LOGO)
    console.print(f"\n  [{CYAN}]fluxlite v1.0[/]")

    setup_now = _confirm("Run setup wizard now? / \u73b0\u5728\u8fdb\u884c\u8bbe\u7f6e?", default=True)
    if setup_now:
        run_wizard()
        return load_config()

    console.print(f"\n  [{DIM}]Edit {CONFIG_PATH} and add your API key[/]")
    console.print(f"  [{DIM}]Then run [bold]fluxlite[/] again[/]")
    sys.exit(0)


