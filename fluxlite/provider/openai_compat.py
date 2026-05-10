import json
import time
import httpx
from typing import Optional

from openai import OpenAI, APIError, Stream
from openai.types.chat import ChatCompletionChunk

from .base import BaseProvider, Message, ToolCall
from ..i18n import _


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 60,
        tools_enabled: bool = True,
    ):
        self.model = model
        self.tools_enabled = tools_enabled
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._httpx = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout=timeout),
        )

    def _build_tools(self, tools: Optional[list[dict]] = None) -> Optional[list[dict]]:
        if not self.tools_enabled or not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": {
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
                },
            }
            for t in tools
        ]

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> Message:
        api_tools = self._build_tools(tools)
        kwargs = {"model": self.model, "messages": messages}
        if api_tools:
            kwargs["tools"] = api_tools

        try:
            resp = self._client.chat.completions.create(**kwargs)
        except APIError as e:
            if "tool" in str(e).lower() or "function" in str(e).lower():
                return self._prompt_injection_chat(messages, tools)
            return Message(role="assistant", content=f"{_('error')}: {e}")

        choice = resp.choices[0]
        msg = choice.message

        if msg.tool_calls:
            return Message(
                role="assistant",
                content=msg.content or "",
                tool_calls=[
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                    for tc in msg.tool_calls
                ],
            )

        return Message(role="assistant", content=msg.content or "")

    def chat_stream(self, messages: list[dict], tools: Optional[list[dict]] = None):
        api_tools = self._build_tools(tools)
        # Serialize manually to preserve reasoning_content in assistant messages
        raw_messages = []
        for m in messages:
            raw_messages.append(dict(m))
        body = {
            "model": self.model,
            "messages": raw_messages,
            "stream": True,
        }
        if api_tools:
            body["tools"] = api_tools

        try:
            raw_body = json.dumps(body, ensure_ascii=False)
            stream_resp = self._httpx.post(
                "/chat/completions",
                content=raw_body,
                headers={"Content-Type": "application/json"},
            )
            stream_resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = e.response.text if hasattr(e, 'response') else str(e)
            if "tool" in detail.lower() or "function" in detail.lower():
                yield from self._prompt_injection_stream(messages, tools)
                return
            yield Message(role="assistant", content=f"{_('error')}: {detail}")
            return
        except Exception as e:
            yield Message(role="assistant", content=f"{_('error')}: {e}")
            return

        collected_content = []
        collected_reasoning = []
        tool_calls_buffer = {}

        for line in stream_resp.iter_lines():
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = chunk_data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                if not delta:
                    continue

                reasoning = delta.get("reasoning_content")
                if reasoning:
                    collected_reasoning.append(reasoning)
                    yield Message(role="assistant", reasoning_content=reasoning)

                content = delta.get("content")
                if content:
                    collected_content.append(content)
                    yield Message(role="assistant", content=content)

                usage_data = chunk_data.get("usage")
                if usage_data:
                    yield Message(role="assistant", usage=usage_data)

                tool_calls_data = delta.get("tool_calls")
                if tool_calls_data:
                    for tc in tool_calls_data:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"id": "", "name": "", "args": ""}
                        tc_id = tc.get("id")
                        if tc_id:
                            tool_calls_buffer[idx]["id"] = tc_id
                        func = tc.get("function", {})
                        fname = func.get("name")
                        if fname:
                            tool_calls_buffer[idx]["name"] += fname
                        fargs = func.get("arguments")
                        if fargs:
                            tool_calls_buffer[idx]["args"] += fargs

        if tool_calls_buffer:
            tool_calls = [
                ToolCall(
                    id=v["id"],
                    name=v["name"],
                    arguments=json.loads(v["args"]) if v["args"] else {},
                )
                for v in tool_calls_buffer.values()
            ]
            yield Message(
                role="assistant",
                content="".join(collected_content),
                tool_calls=tool_calls,
            )

    def _prompt_injection_chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> Message:
        system_prompt = self._build_injection_prompt(tools)
        enhanced = self._inject_system(messages, system_prompt)

        resp = self._client.chat.completions.create(
            model=self.model, messages=enhanced
        )
        content = resp.choices[0].message.content or ""

        tool_calls = self._parse_injection(content)
        if tool_calls:
            clean_content = "\n".join(
                l for l in content.split("\n") if not l.strip().startswith("CMD:")
            )
            return Message(role="assistant", content=clean_content.strip(), tool_calls=tool_calls)

        return Message(role="assistant", content=content)

    def _prompt_injection_stream(self, messages: list[dict], tools: Optional[list[dict]] = None):
        system_prompt = self._build_injection_prompt(tools)
        enhanced = self._inject_system(messages, system_prompt)

        stream = self._client.chat.completions.create(
            model=self.model, messages=enhanced, stream=True
        )

        buffer = ""
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                buffer += delta.content
                yield Message(role="assistant", content=delta.content)

        tool_calls = self._parse_injection(buffer)
        if tool_calls:
            yield Message(role="assistant", content="", tool_calls=tool_calls)

    def _build_injection_prompt(self, tools: Optional[list[dict]] = None) -> str:
        if not tools:
            return ""
        lines = [
            "\n<tools>",
            "\u4f60\u53ef\u4ee5\u4f7f\u7528\u4ee5\u4e0b\u5de5\u5177\uff0c\u5de5\u5177\u8c03\u7528\u683c\u5f0f\u4e3a:",
            "CMD: tool_name(arg1=value1, arg2=value2)",
            "\u6bcf\u6b21\u8c03\u7528\u5355\u72ec\u4e00\u884c\uff0c\u4e0d\u8981\u5199\u5728\u4ee3\u7801\u5757\u91cc\u3002",
            "\u5de5\u5177\u5217\u8868:",
        ]
        for t in tools:
            params = ", ".join(
                f"{k}: {v.get('type', 'str')}" + ("" if v.get("optional") else " [required]")
                for k, v in t.get("parameters", {}).items()
            )
            lines.append(f"- {t['name']}({params}): {t.get('description', '')}")
        lines.append("</tools>")
        return "\n".join(lines)

    def _inject_system(self, messages: list[dict], injection: str) -> list[dict]:
        if not injection:
            return messages
        result = []
        injected = False
        for msg in messages:
            if msg["role"] == "system" and not injected:
                result.append({"role": "system", "content": msg["content"] + "\n\n" + injection})
                injected = True
            else:
                result.append(msg)
        if not injected:
            result.insert(0, {"role": "system", "content": injection})
        return result

    def _parse_injection(self, content: str) -> list[ToolCall]:
        tool_calls = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("CMD:"):
                try:
                    rest = line[4:].strip()
                    name_end = rest.index("(")
                    name = rest[:name_end].strip()
                    args_str = rest[name_end + 1 : rest.rindex(")")]
                    args = {}
                    if args_str.strip():
                        for pair in args_str.split(","):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                k = k.strip()
                                v = v.strip().strip("\"'")
                                args[k] = v
                    tool_calls.append(
                        ToolCall(
                            id=f"cmd_{int(time.time() * 1000)}",
                            name=name,
                            arguments=args,
                        )
                    )
                except (ValueError, IndexError):
                    continue
        return tool_calls
