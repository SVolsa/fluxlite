import json
import time
from dataclasses import dataclass

from ..i18n import _
from ..styles import ICON_TOOL, ICON_ERROR

from . import file_ops
from . import code_exec
from . import web_search
from . import git_ops
from . import code_search
from . import test_runner
from . import hooks
from . import subagent
from . import terminal
from . import planner
from . import network
from . import browser
from .. import plugin_manager
from ..mcp_client import call_tool, get_server_names, get_tool_list, start_server
from ..memory import load_memories, save_memories, add_memory
from ..profile import load_profile, save_profile, add_rule as _add_rule


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict
    handler: callable


def _make_params(**params) -> dict:
    return params


def _memory_write_handler(content: str) -> str:
    add_memory(content)
    return f"Memory recorded: {content[:100]}"


def _memory_read_handler() -> str:
    entries = load_memories()
    if not entries:
        return "No memories recorded."
    result = "\n".join(f"- {e['content']}" for e in entries[-20:])
    return f"Recent memories:\n{result}"


def _rule_add_handler(content: str) -> str:
    profile = load_profile()
    _add_rule(profile, content)
    return f"Rule recorded: {content[:100]}"


def _rule_remove_handler(index: int) -> str:
    profile = load_profile()
    rules = profile.get("rules", [])
    idx = index - 1
    if 0 <= idx < len(rules):
        removed = rules.pop(idx)
        save_profile(profile)
        return f"Rule removed: {removed[:100]}"
    return f"Error: no rule at index {index}"


def _mcp_call_handler(server: str, tool_name: str, arguments: str = "{}") -> str:
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError as e:
        return f"[mcp] Invalid JSON arguments: {e}"
    return call_tool(server, tool_name, args)


def _mcp_list_handler() -> str:
    servers = get_server_names()
    if not servers:
        return (
            "No MCP servers connected.\n"
            "Configure in ~/.fluxlite/mcp.json or use /mcp to manage.\n"
            "Example:\n"
            '  {"servers": [{"name": "github", "command": "node", "args": ["server.js"]}]}'
        )
    tools = get_tool_list()
    if not tools:
        servers_str = ", ".join(servers)
        return f"MCP servers: {servers_str}\n(no tools advertised)"
    lines = [f"MCP: {len(tools)} tools across {len(servers)} servers"]
    for t in tools:
        params = ", ".join(t.get("parameters", {}).get("properties", {}).keys())
        lines.append(f"  [{t['server']}] {t['name']}({params}) — {t.get('description', '')[:60]}")
    return "\n".join(lines)


def _config_set_handler(key: str, value: str) -> str:
    from ..config import load_config, save_config
    cfg = load_config()
    parts = key.split(".")
    target = cfg
    for p in parts[:-1]:
        target = target.setdefault(p, {})
    target[parts[-1]] = value
    save_config(cfg)

    from ..i18n import set_lang
    if key == "app.language":
        set_lang(value)
    return f"Config updated: {key} = {value}"


def _rule_list_handler() -> str:
    from ..profile import load_profile
    profile = load_profile()
    rules = profile.get("rules", [])
    if not rules:
        return "No rules."
    return "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))


TOOLS = [
    ToolDef(
        name="file_write",
        description="\u5199\u5165\u6587\u4ef6\uff08\u5982\u679c\u5b58\u5728\u5219\u8986\u76d6\uff09",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84"},
            content={"type": "string", "desc": "\u6587\u4ef6\u5185\u5bb9"},
        ),
        handler=file_ops.write,
    ),
    ToolDef(
        name="file_read",
        description="\u8bfb\u53d6\u6587\u4ef6\u5185\u5bb9",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84"},
        ),
        handler=file_ops.read,
    ),
    ToolDef(
        name="file_edit",
        description="\u7cbe\u786e\u66ff\u6362\u6587\u4ef6\u4e2d\u7684\u67d0\u6bb5\u6587\u672c",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84"},
            old_string={"type": "string", "desc": "\u9700\u8981\u88ab\u66ff\u6362\u7684\u539f\u6587"},
            new_string={"type": "string", "desc": "\u66ff\u6362\u540e\u7684\u65b0\u6587\u672c"},
        ),
        handler=file_ops.edit,
    ),
    ToolDef(
        name="file_append",
        description="\u5728\u6587\u4ef6\u672b\u5c3e\u8ffd\u52a0\u5185\u5bb9",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84"},
            content={"type": "string", "desc": "\u8981\u8ffd\u52a0\u7684\u5185\u5bb9"},
        ),
        handler=file_ops.append,
    ),
    ToolDef(
        name="file_delete",
        description="\u5220\u9664\u6587\u4ef6",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84"},
        ),
        handler=file_ops.delete,
    ),
    ToolDef(
        name="file_list",
        description="\u5217\u51fa\u76ee\u5f55\u5185\u5bb9\uff08\u652f\u6301 glob \u6a21\u5f0f\u8fc7\u6ee4\uff09",
        parameters=_make_params(
            path={"type": "string", "desc": "\u76ee\u5f55\u8def\u5f84", "optional": True},
            pattern={"type": "string", "desc": "\u8fc7\u6ee4\u6a21\u5f0f (e.g. *.py)", "optional": True},
        ),
        handler=file_ops.list_dir,
    ),
    ToolDef(
        name="code_executor",
        description="\u6267\u884c Python/Bash/Shell \u4ee3\u7801\u6216\u4efb\u610f\u547d\u4ee4\uff08npm, cargo, go, curl \u7b49\uff09\uff0c\u8fd4\u56de stdout/stderr",
        parameters=_make_params(
            language={"type": "string", "desc": "\u8bed\u8a00: python / bash / shell"},
            code={"type": "string", "desc": "\u8981\u6267\u884c\u7684\u4ee3\u7801\u6216\u547d\u4ee4"},
            workdir={"type": "string", "desc": "\u5de5\u4f5c\u76ee\u5f55\uff08\u53ef\u9009\uff0c\u9ed8\u8ba4\u5f53\u524d\u76ee\u5f55\uff09", "optional": True},
            timeout={"type": "number", "desc": "\u8d85\u65f6\u79d2\u6570\uff08\u53ef\u9009\uff0c\u9ed8\u8ba4 30s\uff09", "optional": True},
        ),
        handler=code_exec.execute,
    ),
    ToolDef(
        name="web_search",
        description="\u8054\u7f51\u641c\u7d22\u5f53\u524d\u4fe1\u606f",
        parameters=_make_params(
            query={"type": "string", "desc": "\u641c\u7d22\u5173\u952e\u8bcd"},
            max_results={"type": "number", "desc": "\u8fd4\u56de\u7ed3\u679c\u6570", "optional": True},
        ),
        handler=web_search.search,
    ),
    ToolDef(
        name="memory_write",
        description="\u8bb0\u5f55\u4e00\u6761\u8bb0\u5fc6\uff0c\u7528\u4e8e\u4fdd\u5b58\u91cd\u8981\u4fe1\u606f\u5907\u540e\u7eed\u67e5\u9605",
        parameters=_make_params(
            content={"type": "string", "desc": "\u8bb0\u5fc6\u5185\u5bb9"},
        ),
        handler=_memory_write_handler,
    ),
    ToolDef(
        name="memory_read",
        description="\u67e5\u9605\u5df2\u4fdd\u5b58\u7684\u8bb0\u5fc6",
        parameters=_make_params(),
        handler=_memory_read_handler,
    ),
    ToolDef(
        name="rule_add",
        description="\u6dfb\u52a0\u4e00\u6761\u884c\u4e3a\u89c4\u5219\uff08\u5f53\u7528\u6237\u660e\u786e\u8981\u6c42\u8bb0\u4f4f\u67d0\u6761\u89c4\u5219\uff0c\u6216\u53cd\u590d\u5f3a\u8c03\u540c\u4e00\u884c\u4e3a\u6a21\u5f0f\u65f6\u4f7f\u7528\uff09",
        parameters=_make_params(
            content={"type": "string", "desc": "\u89c4\u5219\u5185\u5bb9\uff0c\u63cf\u8ff0\u5177\u4f53\u5e94\u8be5\u600e\u4e48\u505a"},
        ),
        handler=_rule_add_handler,
    ),
    ToolDef(
        name="rule_remove",
        description="\u79fb\u9664\u4e00\u6761\u884c\u4e3a\u89c4\u5219\uff08\u901a\u8fc7 /memory \u53ef\u67e5\u770b\u5f53\u524d\u89c4\u5219\u5217\u8868\uff09",
        parameters=_make_params(
            index={"type": "number", "desc": "\u8981\u79fb\u9664\u7684\u89c4\u5219\u5e8f\u53f7\uff08\u4ece 1 \u5f00\u59cb\uff09"},
        ),
        handler=_rule_remove_handler,
    ),
    ToolDef(
        name="git_status",
        description="\u67e5\u770b Git \u5de5\u4f5c\u533a\u72b6\u6001\uff08\u5206\u652f\u540d\u3001\u672a\u63d0\u4ea4\u7684\u53d8\u66f4\uff09",
        parameters=_make_params(),
        handler=git_ops.status_handler,
    ),
    ToolDef(
        name="git_diff",
        description="\u67e5\u770b\u672a\u63d0\u4ea4\u7684\u4ee3\u7801\u5dee\u5f02\uff08\u53ef\u6307\u5b9a\u6587\u4ef6\u6216\u67e5\u770b\u5df2\u7f13\u5b58\u7684\u53d8\u66f4\uff09",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84\uff08\u53ef\u9009\uff09", "optional": True},
            staged={"type": "boolean", "desc": "\u662f\u5426\u67e5\u770b\u5df2\u7f13\u5b58\u7684\u53d8\u66f4", "optional": True},
        ),
        handler=git_ops.diff_handler,
    ),
    ToolDef(
        name="git_log",
        description="\u67e5\u770b\u6700\u8fd1\u7684\u63d0\u4ea4\u5386\u53f2",
        parameters=_make_params(
            count={"type": "number", "desc": "\u663e\u793a\u6761\u6570\uff08\u9ed8\u8ba4 10\uff09", "optional": True},
        ),
        handler=git_ops.log_handler,
    ),
    ToolDef(
        name="git_add",
        description="\u7f13\u5b58\u6587\u4ef6\u53d8\u66f4\uff08\u9ed8\u8ba4\u7f13\u5b58\u5168\u90e8\u53d8\u66f4\uff09",
        parameters=_make_params(
            path={"type": "string", "desc": "\u6587\u4ef6\u8def\u5f84\uff08\u9ed8\u8ba4 .\uff09", "optional": True},
        ),
        handler=git_ops.add_handler,
    ),
    ToolDef(
        name="git_commit",
        description="\u63d0\u4ea4\u5df2\u7f13\u5b58\u7684\u53d8\u66f4\u5230\u672c\u5730\u4ed3\u5e93\uff08\u9ed8\u8ba4\u81ea\u52a8\u7f13\u5b58\u6240\u6709\u53d8\u66f4\uff09",
        parameters=_make_params(
            message={"type": "string", "desc": "\u63d0\u4ea4\u6d88\u606f"},
            auto_add={"type": "boolean", "desc": "\u662f\u5426\u81ea\u52a8\u7f13\u5b58\u6240\u6709\u53d8\u66f4\uff08\u9ed8\u8ba4 true\uff09", "optional": True},
        ),
        handler=git_ops.commit_handler,
    ),
    ToolDef(
        name="grep_search",
        description="\u5728\u9879\u76ee\u4ee3\u7801\u4e2d\u641c\u7d22\u5339\u914d\u6b63\u5219\u8868\u8fbe\u5f0f\u7684\u6587\u4ef6\u5185\u5bb9\uff08\u652f\u6301\u8def\u5f84\u8fc7\u6ee4\u548c\u6587\u4ef6\u7c7b\u578b\u8fc7\u6ee4\uff09",
        parameters=_make_params(
            pattern={"type": "string", "desc": "\u641c\u7d22\u7684\u6b63\u5219\u8868\u8fbe\u5f0f"},
            path={"type": "string", "desc": "\u641c\u7d22\u8def\u5f84\uff08\u9ed8\u8ba4\u5f53\u524d\u76ee\u5f55\uff09", "optional": True},
            file_glob={"type": "string", "desc": "\u6587\u4ef6\u8fc7\u6ee4\uff0c\u5982 *.py\u3001*.tsx", "optional": True},
            max_results={"type": "number", "desc": "\u6700\u5927\u8fd4\u56de\u7ed3\u679c\u6570\uff08\u9ed8\u8ba4 40\uff09", "optional": True},
        ),
        handler=code_search.grep_handler,
    ),
    ToolDef(
        name="glob_files",
        description="\u4f7f\u7528 glob \u6a21\u5f0f\u67e5\u627e\u6587\u4ef6\u548c\u76ee\u5f55\uff08\u652f\u6301 **/ \u9012\u5f52\u5339\u914d\uff09",
        parameters=_make_params(
            pattern={"type": "string", "desc": "glob \u6a21\u5f0f\uff0c\u5982 **/*.py\u3001src/**/*.ts"},
            path={"type": "string", "desc": "\u641c\u7d22\u8def\u5f84\uff08\u9ed8\u8ba4\u5f53\u524d\u76ee\u5f55\uff09", "optional": True},
        ),
        handler=code_search.glob_handler,
    ),
    ToolDef(
        name="run_tests",
        description="\u8fd0\u884c\u6d4b\u8bd5\u547d\u4ee4\u5e76\u8fd4\u56de\u7ed3\u6784\u5316\u8f93\u51fa\uff08\u89e3\u6790 pytest/unittest \u7ed3\u679c\uff09",
        parameters=_make_params(
            command={"type": "string", "desc": "\u6d4b\u8bd5\u547d\u4ee4\uff0c\u5982 pytest tests/ -x"},
            path={"type": "string", "desc": "\u8fd0\u884c\u76ee\u5f55\uff08\u9ed8\u8ba4\u5f53\u524d\u76ee\u5f55\uff09", "optional": True},
            timeout={"type": "number", "desc": "\u8d85\u65f6\u79d2\u6570\uff08\u9ed8\u8ba4 120\uff09", "optional": True},
        ),
        handler=test_runner.run_tests,
    ),
    ToolDef(
        name="mcp_call",
        description="\u8c03\u7528 MCP \u670d\u52a1\u5668\u4e0a\u7684\u5de5\u5177\uff08\u5982\u8fde\u63a5\u6570\u636e\u5e93\u3001\u64cd\u4f5c GitHub \u7b49\uff09\u3002\u5148\u7528 mcp_list \u67e5\u770b\u53ef\u7528\u5de5\u5177",
        parameters=_make_params(
            server={"type": "string", "desc": "MCP \u670d\u52a1\u5668\u540d\u79f0"},
            tool_name={"type": "string", "desc": "\u5de5\u5177\u540d\u79f0"},
            arguments={"type": "string", "desc": "JSON \u683c\u5f0f\u7684\u53c2\u6570", "optional": True},
        ),
        handler=_mcp_call_handler,
    ),
    ToolDef(
        name="mcp_list",
        description="\u5217\u51fa\u6240\u6709\u5df2\u8fde\u63a5\u7684 MCP \u670d\u52a1\u5668\u53ca\u5176\u63d0\u4f9b\u7684\u5de5\u5177",
        parameters=_make_params(),
        handler=_mcp_list_handler,
    ),
    ToolDef(
        name="config_set",
        description="\u4fee\u6539 FluxLite \u81ea\u8eab\u8bbe\u7f6e\uff08\u8bed\u8a00\u3001\u5b89\u5168\u6a21\u5f0f\u3001\u8d85\u65f6\u7b49\uff09",
        parameters=_make_params(
            key={"type": "string", "desc": "\u914d\u7f6e\u952e\uff0c\u5982 app.language\u3001api.model"},
            value={"type": "string", "desc": "\u914d\u7f6e\u503c"},
        ),
        handler=_config_set_handler,
    ),
    ToolDef(
        name="rule_list",
        description="\u67e5\u770b\u5f53\u524d\u6240\u6709\u884c\u4e3a\u89c4\u5219",
        parameters=_make_params(),
        handler=_rule_list_handler,
    ),
    ToolDef(
        name="hook_run",
        description="\u624b\u52a8\u89e6\u53d1 hook \u811a\u672c\uff08\u5982 pre_all\u3001post_file_write\u3001\u6216\u5177\u4f53\u811a\u672c\u540d\uff09",
        parameters=_make_params(
            hook_name={"type": "string", "desc": "hook \u540d\u79f0\uff0c\u5982 pre_all\u3001post_code_executor\uff0c\u6216\u811a\u672c\u6587\u4ef6\u540d"},
            args={"type": "string", "desc": "JSON \u683c\u5f0f\u7684\u53c2\u6570", "optional": True},
        ),
        handler=hooks.hook_run_handler,
    ),
    ToolDef(
        name="hook_list",
        description="\u5217\u51fa ~/.fluxlite/hooks/ \u4e0b\u6240\u6709\u5df2\u53d1\u73b0\u7684 hook \u811a\u672c",
        parameters=_make_params(),
        handler=hooks.hook_list_handler,
    ),
    ToolDef(
        name="spawn_agents",
        description="并行启动多个子 AI 代理，各自独立完成子任务。每个代理有独立的 LLM 和工具。tasks 是 JSON 数组",
        parameters=_make_params(
            tasks={"type": "string", "desc": "JSON 数组，每个元素包含 task（任务描述）、可选 tools（工具名列表）、可选 system_prompt"},
            timeout={"type": "number", "desc": "总体超时秒数（默认 300）", "optional": True},
        ),
        handler=subagent.spawn_agents_handler,
    ),
    ToolDef(
        name="terminal",
        description="管理一个持久终端会话，支持连续执行多条命令并保留环境状态。action=start 创建新会话，action=run 执行命令，action=stop 关闭会话",
        parameters=_make_params(
            action={"type": "string", "desc": "操作: start / run / stop / sessions"},
            session_id={"type": "string", "desc": "会话 ID（run/stop 时需要）", "optional": True},
            command={"type": "string", "desc": "要执行的命令（action=run 时需要）", "optional": True},
            timeout={"type": "number", "desc": "超时秒数（默认 60）", "optional": True},
        ),
        handler=terminal.terminal_handler,
    ),
    ToolDef(
        name="task_planner",
        description="创建一个结构化任务计划。先规划步骤再开始执行，减少返工。返回带步骤清单的计划 ID",
        parameters=_make_params(
            goal={"type": "string", "desc": "要完成的目标"},
            steps={"type": "string", "desc": "步骤列表，每行一个（如 \"1. 设计模型\\n2. 编写代码\"）", "optional": True},
            context={"type": "string", "desc": "可选的背景信息", "optional": True},
        ),
        handler=planner.task_planner_handler,
    ),
    ToolDef(
        name="self_review",
        description="对照计划审查已完成的工作。传入 plan_id 和结果摘要，返回审查清单供确认",
        parameters=_make_params(
            plan_id={"type": "string", "desc": "task_planner 返回的计划 ID"},
            result_summary={"type": "string", "desc": "实际完成的结果描述", "optional": True},
            completed_steps={"type": "string", "desc": "已完成的步骤编号（逗号分隔，如 \"1,2,3\"）", "optional": True},
        ),
        handler=planner.self_review_handler,
    ),
    ToolDef(
        name="http_request",
        description="发送 HTTP 请求（GET/POST/PUT/DELETE/PATCH/HEAD），用于调用 API、测试接口、获取网页内容",
        parameters=_make_params(
            method={"type": "string", "desc": "请求方法: GET / POST / PUT / DELETE / PATCH / HEAD", "optional": True},
            url={"type": "string", "desc": "请求 URL（必填）"},
            headers={"type": "string", "desc": "请求头，JSON 格式", "optional": True},
            body={"type": "string", "desc": "请求体（POST/PUT 时使用）", "optional": True},
            timeout={"type": "number", "desc": "超时秒数（默认 30，最大 120）", "optional": True},
        ),
        handler=network.http_request_handler,
    ),
    ToolDef(
        name="file_download",
        description="从 URL 下载文件并保存到本地磁盘，支持大文件、自动推断文件名",
        parameters=_make_params(
            url={"type": "string", "desc": "下载 URL"},
            path={"type": "string", "desc": "保存路径（可选，默认从 URL 推断）", "optional": True},
            timeout={"type": "number", "desc": "超时秒数（默认 120）", "optional": True},
        ),
        handler=network.file_download_handler,
    ),
    ToolDef(
        name="web_scrape",
        description="爬取网页内容，支持提取纯文本、HTML 源码、所有超链接，无需额外依赖",
        parameters=_make_params(
            url={"type": "string", "desc": "目标 URL"},
            extract={"type": "string", "desc": "提取类型: text（可读文本）/ raw（HTML）/ links（链接）/ all", "optional": True},
            selector={"type": "string", "desc": "CSS 选择器（预留，暂未实现）", "optional": True},
            timeout={"type": "number", "desc": "超时秒数（默认 30）", "optional": True},
        ),
        handler=network.web_scrape_handler,
    ),
    ToolDef(
        name="browser",
        description="控制无头浏览器打开网页、点击、填表、截图、执行 JS。需要安装 Playwright (pip install playwright && playwright install chromium)",
        parameters=_make_params(
            action={"type": "string", "desc": "操作: open / click / fill / html / text / title / evaluate / screenshot / close"},
            url={"type": "string", "desc": "导航 URL（action=open 时需要）", "optional": True},
            selector={"type": "string", "desc": "CSS 选择器（click/fill 时需要）", "optional": True},
            text={"type": "string", "desc": "输入文本（fill 时）或截图路径（screenshot 时）", "optional": True},
            script={"type": "string", "desc": "要执行的 JavaScript（evaluate 时）", "optional": True},
            timeout={"type": "number", "desc": "超时秒数（默认 30）", "optional": True},
        ),
        handler=browser.browser_handler,
    ),
]

TOOL_NAME_MAP = {t.name: t for t in TOOLS}


def get_tool_schemas() -> list[dict]:
    builtin = [
        {
            "name": t.name,
            "description": _(t.description),
            "parameters": dict(t.parameters),
        }
        for t in TOOLS
    ]
    builtin.extend(plugin_manager.get_tool_schemas())
    return builtin


def execute_tool(name: str, args: dict) -> str:
    tool = TOOL_NAME_MAP.get(name)
    if not tool:
        for pt in plugin_manager.get_plugin_tools():
            if pt.name == name:
                tool = pt
                break
    if not tool:
        return f"{ICON_ERROR} Unknown tool: {name}"

    hook_pre = hooks.run_pre(name, args)

    try:
        result = tool.handler(**args)
    except PermissionError as e:
        result = f"{ICON_ERROR} {e}"
    except Exception as e:
        result = f"{ICON_ERROR} {name} execution error: {e}"

    hook_post = hooks.run_post(name, args, result)

    if hook_pre:
        result = f"[Hooks]\n{hook_pre}\n\n{result}"
    if hook_post:
        result = f"{result}\n\n[Hooks]\n{hook_post}"

    return result
