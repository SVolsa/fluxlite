import sys
import time

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import Completer, Completion, PathCompleter, merge_completers
from prompt_toolkit.document import Document

console = Console()

_input_history = InMemoryHistory()
_bindings = KeyBindings()

@_bindings.add("enter")
def _(event):
    event.current_buffer.validate_and_handle()


@_bindings.add("escape", "enter")
def _(event):
    event.current_buffer.insert_text("\n")


@_bindings.add("c-r")
def _history_search(event):
    event.current_buffer.start_history_reverse()


_last_esc_time = 0.0
_rewind_flag = False
_REWIND_TIMEOUT = 0.4


@_bindings.add("escape")
def _handle_escape(event):
    global _last_esc_time, _rewind_flag
    now = time.time()
    if now - _last_esc_time < _REWIND_TIMEOUT:
        _rewind_flag = True
        _last_esc_time = 0.0
        event.current_buffer.text = ""
        event.current_buffer.validate_and_handle()
    else:
        _last_esc_time = now


def check_rewind_flag() -> bool:
    global _rewind_flag
    if _rewind_flag:
        _rewind_flag = False
        return True
    return False


CMD_LIST = [
    ("/help",      "show all commands (/h works too)"),
    ("/clear",     "clear the screen"),
    ("/model",     "switch AI model"),
    ("/memory",    "view saved memories and rules"),
    ("/rules",     "list active behavior rules"),
    ("/rule",      "add a behavior rule (usage: /rule <text>)"),
    ("/think",     "toggle model thinking on/off"),
    ("/compact",   "summarize conversation to free context"),
    ("/toolresult","toggle tool result display"),
    ("/export",    "export conversation to Markdown"),
    ("/token",     "toggle token usage display"),
    ("/truncate",  "remove oldest messages to save context"),
    ("/rewind",    "undo last AI response"),
    ("/context",   "show current context usage"),
    ("/tools",     "list all available tools"),
    ("/lang",      "switch language (zh/en)"),
    ("/git",       "run git commands interactively"),
    ("/autocommit","toggle auto-commit after AI file changes"),
    ("/new",       "start a fresh session"),
    ("/search",    "search session history by keyword"),
    ("/sessions",  "browse and load saved sessions"),
    ("/last",      "show current conversation history"),
    ("/plan",      "plan and execute multi-step tasks"),
    ("/mcp",       "manage MCP servers"),
    ("/hooks",     "list hook scripts"),
    ("/plugin",    "manage plugins"),
    ("/sandbox",   "manage sandbox mode"),
    ("/init",      "generate FLUXLITE.md for this project"),
    ("/diff",      "view uncommitted changes"),
    ("/review",    "AI review of code changes"),
    ("/fix",       "auto-fix last error"),
    ("/pin",       "pin/unpin files from truncation"),
    ("/exit",      "exit FluxLite"),
    ("/h",         "alias for /help"),
    ("/s",         "alias for /sessions"),
    ("/p",         "alias for /plan"),
    ("/c",         "alias for /compact"),
    ("/q",         "alias for /exit"),
]

_CMD_DESC_ZH = {
    "/help":       "显示所有命令（可用 /h）",
    "/clear":      "清除屏幕",
    "/model":      "切换 AI 模型",
    "/memory":     "查看已保存的记忆和规则",
    "/rules":      "列出当前行为规则",
    "/rule":       "添加行为规则（用法：/rule <内容>）",
    "/think":      "切换推理模式 on/off",
    "/compact":    "压缩会话以释放上下文",
    "/toolresult": "切换工具结果显示",
    "/export":     "导出对话为 Markdown",
    "/token":      "切换 Token 用量显示",
    "/truncate":   "移除最早消息以节省上下文",
    "/rewind":     "撤销最近 AI 回答",
    "/context":    "显示当前上下文使用情况",
    "/tools":      "列出所有可用工具",
    "/lang":       "切换语言 (zh/en)",
    "/git":        "交互式运行 git 命令",
    "/autocommit": "切换 AI 改动后自动 git 提交",
    "/new":        "开始新会话",
    "/search":     "按关键词搜索历史会话",
    "/sessions":   "浏览和加载历史会话",
    "/last":       "显示当前对话历史",
    "/plan":       "规划并执行多步任务",
    "/mcp":        "管理 MCP 服务器",
    "/hooks":      "列出 hook 脚本",
    "/plugin":     "管理插件",
    "/sandbox":    "管理沙箱模式",
    "/init":       "为当前项目生成 FLUXLITE.md",
    "/diff":       "查看未提交的改动",
    "/review":     "AI 代码审查",
    "/fix":        "自动修复最近的错误",
    "/pin":        "锁定/解锁文件防止截断",
    "/exit":       "退出 FluxLite",
    "/h":          "/help 别名",
    "/s":          "/sessions 别名",
    "/p":          "/plan 别名",
    "/c":          "/compact 别名",
    "/q":          "/exit 别名",
}


class CommandCompleter(Completer):
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        if text.startswith("/"):
            prefix = text[1:].lower()

            try:
                from .i18n import get_lang as _get_lang
                lang = _get_lang()
            except Exception:
                lang = "en"

            for cmd, desc in CMD_LIST:
                cmd_name = cmd[1:]
                if cmd_name.startswith(prefix):
                    if lang == "zh":
                        meta = _CMD_DESC_ZH.get(cmd, desc)
                    else:
                        meta = desc

                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=cmd,
                        display_meta=meta,
                        style="class:completion-menu",
                    )


_multiline_session = None
_single_session = None


def _get_multiline_session():
    global _multiline_session
    if _multiline_session is None:
        _multiline_session = PromptSession(
            history=_input_history,
            key_bindings=_bindings,
            completer=merge_completers([CommandCompleter(), PathCompleter()]),
            complete_while_typing=True,
            multiline=True,
        )
    return _multiline_session


def _get_single_session():
    global _single_session
    if _single_session is None:
        _single_session = PromptSession(
            history=_input_history,
            completer=merge_completers([CommandCompleter(), PathCompleter()]),
            complete_while_typing=True,
            multiline=False,
        )
    return _single_session


def radio_select(title: str, items: list[tuple[str, str]]) -> str | None:
    """行内单选按钮选择（○/● + 上下方向键），避免全屏弹出。"""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    selected = [0]
    result = []
    n = len(items)

    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        selected[0] = (selected[0] - 1) % n
        event.app.invalidate()

    @kb.add("down")
    def _down(event):
        selected[0] = (selected[0] + 1) % n
        event.app.invalidate()

    @kb.add("enter")
    def _enter(event):
        result.append(items[selected[0]][0])
        event.app.exit()

    @kb.add("escape")
    def _esc(event):
        event.app.exit()

    def get_prompt():
        lines = [f"\n  {title}"]
        for i, (k, label) in enumerate(items):
            marker = "●" if i == selected[0] else "○"
            lines.append(f"  {marker} {label}")
        lines.append("")
        return "\n".join(lines)

    try:
        PromptSession(key_bindings=kb).prompt(get_prompt, refresh_interval=0.05)
    except (EOFError, KeyboardInterrupt):
        pass

    sys.stdout.write(f"\033[{n + 4}A\033[J")
    sys.stdout.flush()

    return result[0] if result else None


def get_input(prompt: str = "") -> str:
    try:
        return _get_single_session().prompt(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def read_multiline(prompt: str) -> str:
    try:
        return _get_multiline_session().prompt(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""
