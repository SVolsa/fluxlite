import pytest
from fluxlite.context import build_project_tree, build_git_context


class TestProjectTree:
    def test_returns_string(self):
        result = build_project_tree()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_respects_depth(self):
        deep = build_project_tree(max_depth=0)
        shallow = build_project_tree(max_depth=2)
        assert len(deep.split("\n")) <= len(shallow.split("\n"))


class TestGitContext:
    def test_returns_string(self):
        result = build_git_context()
        assert isinstance(result, str)


class TestTokenEstimate:
    def test_empty(self):
        from fluxlite.commands import estimate_tokens
        assert estimate_tokens("") == 0

    def test_english(self):
        from fluxlite.commands import estimate_tokens
        tokens = estimate_tokens("hello world this is a test")
        assert tokens > 0
        assert tokens < 10  # should be roughly 5-6 tokens

    def test_chinese(self):
        from fluxlite.commands import estimate_tokens
        tokens = estimate_tokens("你好世界这是一个测试")
        assert tokens > 0
        # CJK chars: tiktoken counts ~1 token each, fallback ~2
        assert 5 <= tokens <= 25

    def test_mixed(self):
        from fluxlite.commands import estimate_tokens
        tokens = estimate_tokens("hello 你好 world 世界")
        assert tokens > 0

    def test_long_text(self):
        from fluxlite.commands import estimate_tokens
        text = "hello " * 1000
        tokens = estimate_tokens(text)
        assert tokens > 100  # not just 1
