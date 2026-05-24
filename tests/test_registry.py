import pytest
from fluxlite.tools.registry import TOOLS, TOOL_NAME_MAP, get_tool_schemas, execute_tool


class TestToolRegistry:
    def test_all_tools_have_names(self):
        for t in TOOLS:
            assert t.name, f"Tool missing name"
            assert callable(t.handler), f"Tool {t.name} has no callable handler"

    def test_tool_name_map_matches(self):
        assert len(TOOL_NAME_MAP) == len(TOOLS)

    def test_no_duplicate_names(self):
        names = [t.name for t in TOOLS]
        assert len(names) == len(set(names)), f"Duplicate names: {[n for n in names if names.count(n) > 1]}"

    def test_get_tool_schemas(self):
        schemas = get_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) >= len(TOOLS)
        for s in schemas[:len(TOOLS)]:
            assert "name" in s
            assert "description" in s
            assert "parameters" in s

    def test_execute_unknown_tool(self):
        result = execute_tool("nonexistent_tool_xyz", {})
        assert "Unknown" in result

    def test_file_write_and_read(self):
        result = execute_tool("file_write", {"path": "/tmp/fluxlite_test.txt", "content": "test"})
        assert result
        result = execute_tool("file_read", {"path": "/tmp/fluxlite_test.txt"})
        assert "test" in result

    def test_file_list(self):
        result = execute_tool("file_list", {"path": "."})
        assert result
