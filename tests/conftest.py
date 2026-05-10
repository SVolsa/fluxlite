import pytest
import tempfile
from pathlib import Path


@pytest.fixture(autouse=True)
def temp_fluxlite_dir(monkeypatch, request):
    tmpdir = Path(tempfile.mkdtemp()) / ".fluxlite"
    tmpdir.mkdir(parents=True)
    monkeypatch.setattr("fluxlite.config.CONFIG_DIR", tmpdir)
    monkeypatch.setattr("fluxlite.config.CONFIG_PATH", tmpdir / "config.toml")
    monkeypatch.setattr("fluxlite.config.KEY_FILE", tmpdir / ".fluxkey")
    monkeypatch.setattr("fluxlite.memory.MEMORY_PATH", tmpdir / "memory.json")
    monkeypatch.setattr("fluxlite.app.HISTORY_DIR", tmpdir / "history")
    yield tmpdir
