import json
import time
from typing import Optional

import httpx
from anthropic import Anthropic

from .base import BaseProvider, Message, ToolCall
from ..i18n import _


class AnthropicProvider(BaseProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-sonnet-4-20250514",
        timeout: int = 60,
        tools_enabled: bool = True,
    ):
        self.model = model
        self.tools_enabled = tools_enabled
        self._client = Anthropic(api_key=api_key, base_url=base_url, timeout=timeout)

    def _build_tools(self, tools: Optional[list[dict]] = None) -> Optional[list[dict]]:
        if not self.tools_enabled or not tools:
            return None
        return [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        k: {"type": v.get("type", "string"), "description": v.get("desc", "")}
                        for k, v in t.get("parameters", {}).items()
                    },
                    "required": [
                        k for k, v in t.get("parameters", {}).items()
                        if not v.get("optional", False)
                    ],
                },
            }
            for t in tools
        ]

    def _convert_messages(self, messages: list[dict]) -> tuple[Optional[str], list[dict]]:
        system = None
        converted = []
        for m in messages:
            role = m["role"]
            if role == "system":
                system = m.get("content", "")
                continue
            if role == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", ""),
                        "content": m.get("content", ""),
                    }],
                })
                continue
            content = m.get("content", "")
            tool_calls = m.get("tool_calls")
            if role == "assistant" and tool_calls:
                blocks = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in tool_calls:
                    func = tc.get("function", {})
                    try:
                        inp = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        inp = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": inp,
                    })
                converted.append({"role": "assistant", "content": blocks})
            else:
                converted.append({"role": role, "content": content})
        return system, converted

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> Message:
        api_tools = self._build_tools(tools)
        system, msgs = self._convert_messages(messages)
        kwargs = {"model": self.model, "messages": msgs, "max_tokens": 4096}
        if system:
            kwargs["system"] = system
        if api_tools:
            kwargs["tools"] = api_tools
        try:
            resp = self._client.messages.create(**kwargs)
        except Exception as e:
            return Message(role="assistant", content=f"{_('error')}: {e}")
        content_parts = []
        tool_calls = []
        for block in resp.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=dict(block.input) if isinstance(block.input, dict) else {},
                ))
        return Message(
            role="assistant",
            content="".join(content_parts),
            tool_calls=tool_calls if tool_calls else None,
        )

    def chat_stream(self, messages: list[dict], tools: Optional[list[dict]] = None):
        api_tools = self._build_tools(tools)
        system, msgs = self._convert_messages(messages)
        kwargs = {"model": self.model, "messages": msgs, "max_tokens": 4096, "stream": True}
        if system:
            kwargs["system"] = system
        if api_tools:
            kwargs["tools"] = api_tools

        try:
            with self._client.messages.stream(**kwargs) as stream:
                collected_content = []
                collected_reasoning = []
                tool_calls_buffer = {}
                current_block_index = None

                for event in stream:
                    if event.type == "content_block_start":
                        current_block_index = event.index
                        if hasattr(event, "content_block") and event.content_block.type == "thinking":
                            collected_reasoning.append(event.content_block.thinking or "")
                            yield Message(role="assistant", reasoning_content=event.content_block.thinking or "")
                        elif hasattr(event, "content_block") and event.content_block.type == "tool_use":
                            idx = str(event.index)
                            tool_calls_buffer[idx] = {
                                "id": event.content_block.id or "",
                                "name": event.content_block.name or "",
                                "args": "",
                            }

                    elif event.type == "message_delta":
                        usage_data = event.usage.model_dump() if hasattr(event, "usage") and event.usage else None
                        if usage_data:
                            yield Message(role="assistant", usage=usage_data)

                    elif event.type == "content_block_delta":
                        if hasattr(event, "delta"):
                            if event.delta.type == "thinking_delta":
                                collected_reasoning.append(event.delta.thinking or "")
                                yield Message(role="assistant", reasoning_content=event.delta.thinking or "")
                            elif event.delta.type == "text_delta":
                                collected_content.append(event.delta.text)
                                yield Message(role="assistant", content=event.delta.text)
                            elif event.delta.type == "input_json_delta":
                                idx = str(event.index)
                                if idx not in tool_calls_buffer:
                                    tool_calls_buffer[idx] = {"id": "", "name": "", "args": ""}
                                tool_calls_buffer[idx]["args"] += event.delta.partial_json or ""

                if tool_calls_buffer:
                    tool_calls = []
                    for v in tool_calls_buffer.values():
                        try:
                            args = json.loads(v["args"]) if v["args"] else {}
                        except json.JSONDecodeError:
                            args = {}
                        tool_calls.append(ToolCall(
                            id=v["id"],
                            name=v["name"],
                            arguments=args,
                        ))
                    yield Message(
                        role="assistant",
                        content="".join(collected_content),
                        tool_calls=tool_calls,
                    )

        except Exception as e:
            yield Message(role="assistant", content=f"{_('error')}: {e}")
