from rich.console import Console
from rich.text import Text
from rich.style import Style
from .styles import CYAN, PURPLE, GREEN, GRAY

console = Console()

FONT_NAME = "ansi_shadow"
FALLBACK_LOGO = [
    "  \u2588\u2588\u256d     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u2588\u2588\u2588\u2588  \u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588",
    "  \u2588\u2588\u256d     \u2588\u2588\u256d\u256d\u256d\u2588\u2588\u256d\u256d\u256d\u2588\u2588\u256d\u256d\u256d\u256d\u2588\u2588\u256d\u256d\u2588\u2588\u256d\u256d\u2588\u2588\u2588\u2588\u256d\u256d\u256d\u2588\u2588\u256d\u256d\u256d\u2588\u2588\u256d\u256d\u2588\u2588\u256d\u256d\u256d",
    "  \u2588\u2588\u256d     \u2588\u2588\u256d   \u2588\u2588\u256d   \u2588\u2588\u2588\u2588\u2588\u256d  \u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u256d   \u2588\u2588\u256d   \u2588\u2588\u256d",
    "  \u2588\u2588\u256d     \u2588\u2588\u256d   \u2588\u2588\u256d   \u2588\u2588\u256d\u256d\u256d\u256d  \u2588\u2588\u256d\u256d\u2588\u2588\u2588\u2588\u256d   \u2588\u2588\u256d   \u2588\u2588\u256d",
    "  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u256d   \u2588\u2588\u256d   \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u2588\u2588\u2588\u2588\u256d\u2588\u2588\u2588\u2588\u2588\u2588\u256d   \u2588\u2588\u256d",
    "  \u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d   \u256d\u256d\u256d   \u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d\u256d    \u256d\u256d\u256d",
    "                                                                      ",
]

try:
    import pyfiglet
    HAS_FIGLET = True
except ImportError:
    HAS_FIGLET = False


def run_startup(language: str = "zh"):
    console.clear()

    if HAS_FIGLET:
        try:
            logo_str = pyfiglet.figlet_format("FluxLite", font=FONT_NAME)
            console.print(Text(logo_str, style=Style(color=CYAN, bold=True)))
        except Exception:
            for line in FALLBACK_LOGO:
                console.print(Text(line, style=Style(color=CYAN, bold=True)))
    else:
        for line in FALLBACK_LOGO:
            console.print(Text(line, style=Style(color=CYAN, bold=True)))

    console.print(Text("  v0.1.0  |  Tools: Code \u00b7 Search \u00b7 Files", style=Style(color=PURPLE)))
    console.print()


