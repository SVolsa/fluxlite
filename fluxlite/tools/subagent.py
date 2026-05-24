"""Sub-agent system: spawn parallel AI agents for independent tasks.

Each sub-agent runs in its own thread with a separate provider instance.
Uses non-streaming chat for efficiency.
"""
import json
import threading
from ..provider import create_provider

_provider_config: dict = {}


def init(api_key: str, base_url: str, model: str, timeout: int):
    _provider_config.update(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
    )


def _run_subagent(task_desc: str, tool_names: list[str] | None, system_prompt: str | None) -> str:
    from .registry import execute_tool, TOOLS
    from ..tools.registry import get_tool_schemas

    try:
        provider = create_provider(**_provider_config)
    except Exception as e:
        return f"[subagent] Failed to create provider: {e}"

    if tool_names:
        tool_set = [t for t in TOOLS if t.name in tool_names]
    else:
        tool_set = TOOLS
    tool_schemas = [
        {"name": t.name, "description": t.description, "parameters": dict(t.parameters)}
        for t in tool_set
    ]

    tool_desc_lines = []
    for t in tool_set:
        params = ", ".join(f"{k}: {v.get('type', 'str')}" for k, v in t.parameters.items())
        tool_desc_lines.append(f"- {t.name}({params}): {t.description}")
    tool_block = "\n".join(tool_desc_lines)

    sp = system_prompt or (
        "You are a helpful sub-agent. Complete your assigned task using the available tools.\n"
        "Return a concise answer when done.\n\n"
        f"Available tools:\n{tool_block}"
    )

    messages = [{"role": "system", "content": sp}, {"role": "user", "content": task_desc}]

    for turn in range(5):
        try:
            result = provider.chat(messages, tool_schemas)
        except Exception as e:
            return f"[subagent] LLM error: {e}"

        content = result.content or ""
        tool_calls = result.tool_calls or []

        if not tool_calls:
            return content if content else "(empty response)"

        openai_calls = []
        for tc in tool_calls:
            openai_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            })

        msg = {"role": "assistant", "content": content, "tool_calls": openai_calls}
        messages.append(msg)

        for tc in tool_calls:
            tool_result = execute_tool(tc.name, tc.arguments)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})

    return "[subagent] Max turns reached"


def spawn_agents_handler(tasks_json: str, timeout: int = 300) -> str:
    try:
        tasks = json.loads(tasks_json)
    except json.JSONDecodeError as e:
        return f"[error] Invalid tasks JSON: {e}"

    if not isinstance(tasks, list):
        return "[error] tasks must be a JSON array"

    if not _provider_config:
        return "[error] Sub-agent not initialized (missing provider config)"

    results: dict[int, str] = {}
    threads: list[threading.Thread] = []

    def _worker(idx: int, task: dict):
        try:
            results[idx] = _run_subagent(
                task.get("task", ""),
                task.get("tools"),
                task.get("system_prompt"),
            )
        except Exception as e:
            results[idx] = f"[error] {e}"

    for i, task in enumerate(tasks):
        t = threading.Thread(target=_worker, args=(i, task), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=timeout)

    for i, t in enumerate(threads):
        if t.is_alive():
            results[i] = "[subagent] TIMEOUT"

    lines = []
    for i, task in enumerate(tasks):
        result = results.get(i, "[subagent] No result")
        task_label = task.get("task", f"Task {i+1}")[:80]
        lines.append(f"=== Agent {i+1}: {task_label} ===")
        lines.append(result[:2000])
        if len(result) > 2000:
            lines.append("...(truncated)")
        lines.append("")

    return "\n".join(lines).strip()
