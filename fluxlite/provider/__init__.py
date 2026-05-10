from .openai_compat import OpenAIProvider
from .anthropic import AnthropicProvider


def create_provider(
    api_key: str,
    base_url: str,
    model: str,
    timeout: int = 60,
    tools_enabled: bool = True,
):
    if "anthropic" in base_url.lower():
        return AnthropicProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            tools_enabled=tools_enabled,
        )
    return OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        tools_enabled=tools_enabled,
    )


def detect_provider_type(base_url: str) -> str:
    url = base_url.lower()
    if "deepseek" in url:
        return "deepseek"
    if "groq" in url:
        return "groq"
    if "openrouter" in url:
        return "openrouter"
    if "anthropic" in url:
        return "anthropic"
    if "openai" in url and "azure" not in url:
        return "openai"
    return ""
