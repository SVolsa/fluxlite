import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

import fluxlite.memory as mem


class TestMemory:
    def _memory(self):
        """Return fresh isolated memory dict."""
        return mem.load_memory()

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_load_default(self, _):
        memory = self._memory()
        assert "identity" in memory
        assert "memories" in memory
        assert "rules" in memory
        assert memory["identity"]["name"] == ""

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_save_and_load(self, _):
        memory = self._memory()
        memory["identity"]["name"] = "TestBot"
        memory["identity"]["user_name"] = "Tester"
        mem.save_memory(memory)
        loaded = mem.load_memory()
        assert loaded["identity"]["name"] == "TestBot"
        assert loaded["identity"]["user_name"] == "Tester"

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_add_memory(self, _):
        memory = self._memory()
        mem.add_memory(memory, "User likes Python")
        assert len(memory["memories"]) == 1
        assert memory["memories"][0]["content"] == "User likes Python"

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_multiple_memories(self, _):
        memory = self._memory()
        mem.add_memory(memory, "Memory 1")
        mem.add_memory(memory, "Memory 2")
        mem.add_memory(memory, "Memory 3")
        assert len(memory["memories"]) == 3

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_add_rule(self, _):
        memory = self._memory()
        mem.add_rule(memory, "Be concise")
        assert len(memory["rules"]) == 1
        assert memory["rules"][0] == "Be concise"

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_remove_rule(self, _):
        memory = self._memory()
        mem.add_rule(memory, "Rule 1")
        mem.add_rule(memory, "Rule 2")
        assert mem.remove_rule(memory, 0) is True
        assert len(memory["rules"]) == 1
        assert memory["rules"][0] == "Rule 2"

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_remove_rule_invalid_index(self, _):
        memory = self._memory()
        assert mem.remove_rule(memory, 5) is False
        assert mem.remove_rule(memory, -1) is False

    @patch("fluxlite.memory.MEMORY_PATH", new_callable=lambda: Path(tempfile.mkdtemp()) / "mem.json")
    def test_memory_persistence(self, _):
        memory = self._memory()
        mem.add_memory(memory, "Persistent memory")
        loaded = mem.load_memory()
        assert len(loaded["memories"]) == 1
        assert loaded["memories"][0]["content"] == "Persistent memory"
