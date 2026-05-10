import time
from dataclasses import dataclass

from ..i18n import _
from ..styles import ICON_TOOL, ICON_ERROR

from . import file_ops
from . import code_exec
from . import web_search
from ..memory import load_memory, save_memory, add_memory


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict
    handler: callable


def _make_params(**params) -> dict:
    return params


def _memory_write_handler(content: str) -> str:
    memory = load_memory()
    add_memory(memory, content)
    return f"Memory recorded: {content[:100]}"


def _memory_read_handler() -> str:
    memory = load_memory()
    entries = memory.get("memories", [])
    if not entries:
        return "No memories recorded."
    result = "\n".join(f"- {e['content']}" for e in entries[-20:])
    return f"Recent memories:\n{result}"


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
        description="\u6267\u884c Python \u6216 Bash \u4ee3\u7801\uff0c\u8fd4\u56de stdout/stderr",
        parameters=_make_params(
            language={"type": "string", "desc": "\u8bed\u8a00: python \u6216 bash"},
            code={"type": "string", "desc": "\u8981\u6267\u884c\u7684\u4ee3\u7801"},
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
]

TOOL_NAME_MAP = {t.name: t for t in TOOLS}


def get_tool_schemas() -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": dict(t.parameters),
        }
        for t in TOOLS
    ]


def execute_tool(name: str, args: dict) -> str:
    tool = TOOL_NAME_MAP.get(name)
    if not tool:
        return f"{ICON_ERROR} Unknown tool: {name}"

    try:
        result = tool.handler(**args)
        return result
    except PermissionError as e:
        return f"{ICON_ERROR} {e}"
    except Exception as e:
        return f"{ICON_ERROR} {name} execution error: {e}"
