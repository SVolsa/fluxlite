from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: str
    content: str = ""
    reasoning_content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    usage: Optional[dict] = None


class BaseProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> Message:
        ...

    @abstractmethod
    def chat_stream(self, messages: list[dict], tools: Optional[list[dict]] = None):
        ...
