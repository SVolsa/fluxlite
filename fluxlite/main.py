import sys
import argparse

from .config import load_config, CONFIG_PATH, is_configured
from .i18n import _, set_lang
from .startup import run_startup
from .app import run_app
from .wizard import run_wizard


def main():
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
    parser.add_argument("--version", "-V", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        print("fluxlite v0.1.0")
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
    api_key = cfg.get("api", {}).get("key", "")
    tavily_key = cfg.get("tavily", {}).get("key", "")
    timeout = cfg.get("app", {}).get("timeout", 60)
    safe_mode = cfg.get("app", {}).get("safe_mode", True)

    if not args.no_logo:
        run_startup(language=lang)

    run_app(
        api_key=api_key,
        base_url=base_url,
        model=model,
        tavily_key=tavily_key,
        timeout=timeout,
        safe_mode=safe_mode,
        lang=lang,
    )


if __name__ == "__main__":
    main()


