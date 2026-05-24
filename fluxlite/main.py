import os
import sys
import argparse

_REQUIRED_DEPS = {
    "httpx": "pip install httpx",
    "rich": "pip install rich",
    "prompt_toolkit": "pip install prompt_toolkit",
    "openai": "pip install openai",
    "pygments": "pip install pygments",
    "pyfiglet": "pip install pyfiglet",
    "tomli_w": "pip install tomli-w",
    "cryptography": "pip install cryptography",
}


def _check_deps():
    missing = []
    for mod, hint in _REQUIRED_DEPS.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(f"  {mod}  ({hint})")
    if missing:
        print("Missing dependencies:\n")
        for m in missing:
            print(m)
        print("\nInstall all: pip install fluxlite[full]")
        sys.exit(1)


def main():
    _check_deps()

    from .config import load_config, CONFIG_PATH, is_configured
    from .i18n import _, set_lang
    from .startup import run_startup
    from .app import run_app
    from .wizard import run_wizard
    parser = argparse.ArgumentParser(
        description="fluxlite - Lightweight AI CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands in chat:\n"
            "  /help   - Show help\n"
            "  /model  - Switch model\n"
            "  /lang   - Switch language\n"
            "  /clear  - Clear screen\n"
            "  /tools  - List tools\n"
            "  /exit   - Exit\n"
            "\nFirst time? Run with --wizard to setup interactively"
        ),
    )
    parser.add_argument("--wizard", action="store_true", help="Run setup wizard")
    parser.add_argument("--model", "-m", help="Model name")
    parser.add_argument("--lang", "-l", help="Language (zh/en)", choices=["zh", "en"])
    parser.add_argument("--no-logo", action="store_true", help="Skip startup animation")
    parser.add_argument("--auto", "-a", action="store_true", help="Auto-execute tools in non-interactive mode")
    parser.add_argument("--version", "-V", action="store_true", help="Show version")
    parser.add_argument("prompt", nargs="?", help="Prompt for one-shot non-interactive mode")
    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"fluxlite {__version__}")
        return

    if args.wizard or not is_configured():
        if not is_configured():
            print("\n  fluxlite - First-time setup required\n")
        run_wizard()
        if args.wizard:
            return

    cfg = load_config()

    lang = cfg.get("app", {}).get("language", "zh")
    if args.lang:
        lang = args.lang
    set_lang(lang)

    model = cfg.get("api", {}).get("model", "deepseek-chat")
    if args.model:
        model = args.model
    base_url = cfg.get("api", {}).get("base_url", "https://api.deepseek.com")
    api_key = cfg.get("api", {}).get("key", "") or os.environ.get("OPENAI_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    tavily_key = cfg.get("tavily", {}).get("key", "") or os.environ.get("TAVILY_API_KEY", "")
    timeout = cfg.get("app", {}).get("timeout", 60)
    safe_mode = cfg.get("app", {}).get("safe_mode", True)

    if not args.no_logo and not args.prompt:
        run_startup(language=lang)

    run_app(
        api_key=api_key,
        base_url=base_url,
        model=model,
        tavily_key=tavily_key,
        timeout=timeout,
        safe_mode=safe_mode,
        lang=lang,
        prompt=args.prompt or "",
        auto_mode=args.auto,
    )


if __name__ == "__main__":
    main()


