import sys
from rich.style import Style

# Color scheme (dark theme)
CYAN = "#00f5d4"
GREEN = "#00ff9d"
PURPLE = "#b388ff"
ORANGE = "#ffb347"
RED = "#ff5370"
BLUE = "#82aaff"
YELLOW = "#ffd760"
WHITE = "#ffffff"
GRAY = "#545454"
DIM = "#3a3a3a"

# Additional UI colors
GRAY_LIGHT = "#cccccc"     # User message text
WHITE_SOFT = "#e0e0e0"    # AI response body text
BOLD = "bold"

# Check if terminal supports Unicode/emoji
_SUPPORTS_UTF = sys.stdout.encoding and (
    "utf" in sys.stdout.encoding.lower() or "65001" in sys.stdout.encoding
)

# Windows GBK-safe icons
if _SUPPORTS_UTF:
    ICON_TOOL = "\u26a1"
    ICON_FILE = "\U0001f4c1"
    ICON_CODE = "\U0001f4bb"
    ICON_SEARCH = "\U0001f50d"
    ICON_OUTPUT = "\U0001f4ca"
    ICON_ERROR = "\u2717"
    ICON_OK = "\u2713"
    ICON_USER = "\U0001f9d1"
    ICON_BOT = "\U0001f916"
else:
    ICON_TOOL = "!"
    ICON_FILE = "#"
    ICON_CODE = "$"
    ICON_SEARCH = "?"
    ICON_OUTPUT = ">"
    ICON_ERROR = "x"
    ICON_OK = "v"
    ICON_USER = "[You]"
    ICON_BOT = "[Bot]"

# Style objects
STYLE_USER = Style(color=GREEN, bold=True)
STYLE_BOT = Style(color=CYAN, bold=True)
STYLE_TOOL = Style(color=ORANGE, italic=True)
STYLE_TOOL_RESULT = Style(color=YELLOW)
STYLE_ERROR = Style(color=RED, bold=True)
STYLE_TIMESTAMP = Style(color=GRAY)
STYLE_PATH = Style(color=YELLOW, underline=True)
STYLE_URL = Style(color=BLUE, underline=True)
STYLE_CODE = Style(color="#a8cc8c")
STYLE_DIM = Style(color=DIM)
