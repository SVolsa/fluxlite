import pytest
from fluxlite.provider.base import Message, ToolCall
from fluxlite.provider import create_provider, detect_provider_type


class TestMessageModel:
    def test_default_fields(self):
        msg = Message(role="assistant")
        assert msg.role == "assistant"
        assert msg.content == ""
        assert msg.reasoning_content == ""
        assert msg.tool_calls == []
        assert msg.usage is None

    def test_content_message(self):
        msg = Message(role="assistant", content="Hello")
        assert msg.content == "Hello"

    def test_reasoning_message(self):
        msg = Message(role="assistant", content="Answer", reasoning_content="Thinking...")
        assert msg.reasoning_content == "Thinking..."
        assert msg.content == "Answer"

    def test_tool_call_message(self):
        tc = ToolCall(id="call_1", name="file_read", arguments={"path": "/test"})
        msg = Message(role="assistant", tool_calls=[tc])
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "file_read"
        assert msg.tool_calls[0].arguments == {"path": "/test"}

    def test_usage_message(self):
        msg = Message(role="assistant", content="Hi", usage={"total_tokens": 50})
        assert msg.usage["total_tokens"] == 50


class TestProviderFactory:
    def test_detect_deepseek(self):
        assert detect_provider_type("https://api.deepseek.com") == "deepseek"

    def test_detect_openai(self):
        assert detect_provider_type("https://api.openai.com/v1") == "openai"

    def test_detect_openrouter(self):
        assert detect_provider_type("https://openrouter.ai/api/v1") == "openrouter"

    def test_detect_groq(self):
        assert detect_provider_type("https://api.groq.com/openai/v1") == "groq"

    def test_detect_anthropic(self):
        assert detect_provider_type("https://api.anthropic.com") == "anthropic"

    def test_detect_unknown(self):
        assert detect_provider_type("https://custom.example.com") == ""

    def test_create_openai_provider(self):
        provider = create_provider("sk-key", "https://api.deepseek.com", "deepseek-chat")
        from fluxlite.provider.openai_compat import OpenAIProvider
        assert isinstance(provider, OpenAIProvider)

    def test_create_anthropic_provider(self):
        provider = create_provider("sk-key", "https://api.anthropic.com", "claude-sonnet-4-20250514")
        from fluxlite.provider.anthropic import AnthropicProvider
        assert isinstance(provider, AnthropicProvider)

    def test_create_defaults_to_openai(self):
        provider = create_provider("sk-key", "https://unknown.com", "gpt-4o")
        from fluxlite.provider.openai_compat import OpenAIProvider
        assert isinstance(provider, OpenAIProvider)
