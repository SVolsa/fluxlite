import os
import tempfile
from pathlib import Path
import pytest
from fluxlite.tools import file_ops


class TestFileWrite:
    def test_write_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            result = file_ops.write(str(f), "hello world")
            assert f.exists()
            assert f.read_text() == "hello world"
            assert "Written" in result

    def test_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_text("old")
            result = file_ops.write(str(f), "new")
            assert f.read_text() == "new"
            assert "Written" in result


class TestFileRead:
    def test_read_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_text("hello world")
            result = file_ops.read(str(f))
            assert "hello world" in result

    def test_read_not_found(self):
        result = file_ops.read("/nonexistent/path_12345.txt")
        assert "not found" in result.lower() or "file not found" in result.lower()


class TestFileEdit:
    def test_replace_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_text("hello world")
            result = file_ops.edit(str(f), "hello", "goodbye")
            assert f.read_text() == "goodbye world"
            assert "Replaced" in result

    def test_old_string_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_text("hello world")
            result = file_ops.edit(str(f), "nonexistent", "replacement")
            assert "not found" in result


class TestFileAppend:
    def test_append_to_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_text("hello")
            result = file_ops.append(str(f), " world")
            assert f.read_text() == "hello world"
            assert "Appended" in result

    def test_append_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "new.txt"
            result = file_ops.append(str(f), "content")
            assert f.exists()
            assert f.read_text() == "content"


class TestFileDelete:
    def test_delete_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.txt"
            f.write_text("hello")
            result = file_ops.delete(str(f))
            assert not f.exists()
            assert "Deleted" in result

    def test_delete_not_found(self):
        result = file_ops.delete("/nonexistent/path_12345.txt")
        assert "not found" in result.lower()


class TestFileList:
    def test_list_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.txt").write_text("a")
            (Path(tmp) / "b.py").write_text("b")
            (Path(tmp) / "sub").mkdir()
            result = file_ops.list_dir(tmp)
            assert "a.txt" in result
            assert "b.py" in result
            assert "sub/" in result

    def test_list_with_glob(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("a")
            (Path(tmp) / "b.txt").write_text("b")
            result = file_ops.list_dir(tmp, "*.py")
            assert "a.py" in result
            assert "b.txt" not in result

    def test_list_nonexistent(self):
        result = file_ops.list_dir("/nonexistent_dir_12345")
        assert "not found" in result.lower()


class TestSafePath:
    def test_normal_path_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, msg = file_ops._safe_path(tmp)
            assert msg == ""
            assert p == Path(tmp).resolve()

    def test_system_path_blocked(self):
        if os.name == "nt":
            with pytest.raises(PermissionError):
                file_ops._safe_path("C:\\Windows\\System32\\test.txt")
        else:
            with pytest.raises(PermissionError):
                file_ops._safe_path("/etc/passwd")
