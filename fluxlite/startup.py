"""Startup screen with ASCII logo and tips."""
import os
import re as _re

from rich.console import Console
from rich.text import Text
from rich.style import Style
from .styles import CYAN, PURPLE, GREEN, GRAY

console = Console()

FONT_NAME = "sub-zero"
FALLBACK_LOGO = [
    " ______   __         __  __     __  __    ",
    r"/\  ___\ /\ \       /\ \/\ \   /\_\_\_\   ",
    r"\ \  __\ \ \ \____  \ \ \_\ \  \/_/\_\/_  ",
    r" \ \_\    \ \_____\  \ \_____\   /\_\/\_\ ",
    r"  \/_/     \/_____/   \/_____/   \/_/\/_/ ",
]

try:
    import pyfiglet
    HAS_FIGLET = True
except ImportError:
    HAS_FIGLET = False

TIPS = [
    "Try /help to see all available commands",
    "Use /plan for multi-step tasks with auto-review",
    "/memory saves important info across sessions",
    "Plugins extend FluxLite with custom tools",
    "Double-press Esc to cancel AI response",
    "Use /search to find past conversations",
    "/sandbox isolates file operations for safety",
    "Use /model to switch AI models on the fly",
    "Hooks let you run scripts before/after tools",
    "/sessions saves and restores conversations",
    "Use /mcp to connect external services",
    "Customize behavior with /rules",
]

_tip_index = 0


def _next_tip() -> str:
    global _tip_index
    tip = TIPS[_tip_index % len(TIPS)]
    _tip_index += 1
    return tip


def _get_logo_lines() -> list[str]:
    if HAS_FIGLET:
        try:
            logo_str = pyfiglet.figlet_format("FLUX", font=FONT_NAME, width=200)
            return [l.rstrip() for l in logo_str.split("\n") if l.strip()]
        except Exception:
            pass
    return [l for l in FALLBACK_LOGO if l.strip()]


def print_header(model: str = ""):
    logo_lines = _get_logo_lines()
    logo_w = max((len(l) for l in logo_lines), default=0)

    try:
        term_w = os.get_terminal_size().columns
    except Exception:
        term_w = 80

    box_w = max(min(term_w, 100), logo_w + 4)
    inner = box_w - 2
    label = "FluxLite v1.0"

    top_prefix = f"╭───{label} "
    top_remain = box_w - len(top_prefix) - 1
    console.print(Text(top_prefix + "─" * top_remain + "╮", style=GRAY))

    # ASCII logo: pad and center
    max_logo_w = max(len(l) for l in logo_lines)
    pad_l = (inner - max_logo_w) // 2
    for line in logo_lines:
        row = Text("│", style=GRAY)
        row.append(" " * pad_l + line.ljust(max_logo_w) + " " * (inner - max_logo_w - pad_l),
                   style=Style(color=CYAN, bold=True))
        row.append("│", style=GRAY)
        console.print(row)

    # Spacer
    console.print(Text(f"│{' ' * inner}│", style=GRAY))

    # Info rows
    tip = _next_tip()
    left_w = inner * 3 // 5
    right_w = inner - left_w - 5

    left_raw = [("Tip:", tip)]
    if model:
        left_raw.append(("Model:", model))

    right_raw = [
        ("Version", "0.5.4"),
        ("Author:", "Volsa"),
        ("GitHub:", "svolsa"),
    ]

    for i in range(max(len(left_raw), len(right_raw))):
        l_label, l_content = left_raw[i] if i < len(left_raw) else ("", "")
        r_label, r_content = right_raw[i] if i < len(right_raw) else ("", "")

        # Truncate content to fit column width
        l_avail = left_w - len(l_label) - 1 if l_label else left_w
        r_avail = right_w - len(r_label) - 1 if r_label else right_w
        l_content = l_content[:max(0, l_avail)]
        r_content = r_content[:max(0, r_avail)]

        l_str = (l_label + " " + l_content).ljust(left_w) if l_label else " " * left_w
        r_str = (r_label + " " + r_content).ljust(right_w) if r_label else " " * right_w

        row = Text("│ ", style=GRAY)

        if l_label:
            row.append(l_label, style=Style(color=CYAN))
            row.append(l_str[len(l_label):])
        else:
            row.append(l_str)

        row.append(" │ ", style=GRAY)

        if r_label:
            row.append(r_label, style=Style(color=CYAN))
            row.append(r_str[len(r_label):])
        else:
            row.append(r_str)

        row.append(" │", style=GRAY)
        console.print(row)

    # Spacer
    console.print(Text(f"│{' ' * inner}│", style=GRAY))

    bottom_label = "/help  /tools  /memory  /exit"
    bottom_prefix = f"╰───{bottom_label} "
    bottom_remain = box_w - len(bottom_prefix) - 1
    console.print(Text(bottom_prefix + "─" * bottom_remain + "╯", style=GRAY))


def print_logo():
    for line in _get_logo_lines():
        console.print(Text(line, style=Style(color=CYAN, bold=True)))


def run_startup(language: str = "zh"):
    import sys
    sys.stdout.write("\033]0;FluxLite\007")
    sys.stdout.flush()

    console.clear()
    print_header(model="")
    console.print()
