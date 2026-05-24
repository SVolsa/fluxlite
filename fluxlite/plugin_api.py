"""FluxLite Plugin API — public interface for plugin developers.

Plugins are folders in ~/.fluxlite/plugins/<name>/ containing:
  - <name>.json   — metadata + tool definitions
  - <name>.py     — handler functions

Each handler receives a single `args: dict` and must return `str`.
"""

import json as _json
import uuid as _uuid
from datetime import datetime as _datetime
from pathlib import Path


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


def format_result(data: dict | list | str) -> str:
    """Format dict/list as pretty JSON, or return string as-is."""
    if isinstance(data, (dict, list)):
        return _json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


def read_file(path: str) -> str:
    """Read a text file and return its contents."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        raise PluginError(f"read_file failed: {e}")


def write_file(path: str, content: str) -> str:
    """Write text content to a file. Returns the absolute path."""
    try:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return str(dest.resolve())
    except Exception as e:
        raise PluginError(f"write_file failed: {e}")


def run_command(command: str, timeout: int = 30) -> str:
    """Execute a shell command and return stdout+stderr."""
    import subprocess
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout,
        )
        parts = []
        if r.stdout.strip():
            parts.append(r.stdout.strip())
        if r.stderr.strip():
            parts.append(f"[stderr]\n{r.stderr.strip()}")
        if r.returncode != 0:
            parts.append(f"(exit {r.returncode})")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return f"[timeout after {timeout}s]"
    except Exception as e:
        return f"[error: {e}]"


def http_get(url: str, headers: str = "", timeout: int = 30) -> str:
    """Send a GET request and return formatted response."""
    import httpx
    try:
        parsed = _json.loads(headers) if headers else {}
        r = httpx.get(url, headers=parsed or None, timeout=timeout, follow_redirects=True)
        if "application/json" in r.headers.get("content-type", ""):
            return _json.dumps(r.json(), ensure_ascii=False, indent=2)
        return r.text[:5000]
    except Exception as e:
        return f"[http_get error: {e}]"


def grep(pattern: str, path: str = ".", file_glob: str = "") -> str:
    """Search for a regex pattern in files."""
    import subprocess
    cmd = ["grep", "-rn", pattern, path, "--color=never"]
    if file_glob:
        cmd.extend(["--include", file_glob])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout.strip()[:3000] or "(no matches)"
    except Exception as e:
        return f"[grep error: {e}]"


# ── New APIs ──


def http_post(url: str, data: str = "", headers: str = "", timeout: int = 30) -> str:
    """发送 POST 请求 / Send a POST request.

    data 会自动 JSON 编码（如果是 dict/list）; headers 为 JSON 字符串。
    """
    import httpx
    try:
        parsed_headers = _json.loads(headers) if headers else None
        body = None
        if data:
            try:
                body = _json.loads(data)
            except _json.JSONDecodeError:
                body = data
        r = httpx.post(url, json=body if isinstance(body, (dict, list)) else None,
                       content=body if isinstance(body, str) else None,
                       headers=parsed_headers, timeout=timeout, follow_redirects=True)
        if "application/json" in r.headers.get("content-type", ""):
            return _json.dumps(r.json(), ensure_ascii=False, indent=2)
        return r.text[:5000]
    except Exception as e:
        return f"[http_post error: {e}]"


def json_parse(text: str) -> str:
    """安全解析 JSON 字符串 / Safely parse a JSON string."""
    try:
        data = _json.loads(text)
        return _json.dumps(data, ensure_ascii=False, indent=2)
    except _json.JSONDecodeError as e:
        return f"[json_parse error] Invalid JSON: {e}"


def load_json(path: str) -> str:
    """读取并解析 JSON 文件 / Read and parse a JSON file."""
    try:
        data = _json.loads(Path(path).read_text(encoding="utf-8"))
        return _json.dumps(data, ensure_ascii=False, indent=2)
    except FileNotFoundError:
        return f"[load_json error] File not found: {path}"
    except _json.JSONDecodeError as e:
        return f"[load_json error] Invalid JSON: {e}"
    except Exception as e:
        return f"[load_json error] {e}"


def save_json(path: str, data: str) -> str:
    """将数据序列化为 JSON 并写入文件 / Serialize data as JSON and write to file.

    data 应为 JSON 字符串。
    """
    try:
        parsed = _json.loads(data)
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            _json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(dest.resolve())
    except _json.JSONDecodeError as e:
        return f"[save_json error] Invalid JSON: {e}"
    except Exception as e:
        return f"[save_json error] {e}"


def list_dir(path: str = ".") -> str:
    """列出目录内容 / List directory contents."""
    try:
        p = Path(path)
        if not p.is_dir():
            return f"[list_dir error] Not a directory: {path}"
        entries = []
        for entry in sorted(p.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return "\n".join(entries) if entries else "(empty directory)"
    except Exception as e:
        return f"[list_dir error] {e}"


def uuid_gen() -> str:
    """生成 UUID v4 / Generate a UUID v4 string."""
    return str(_uuid.uuid4())


def timestamp() -> str:
    """获取当前 ISO 8601 时间戳 / Get current ISO 8601 timestamp."""
    return _datetime.now().isoformat()


def env_get(key: str, default: str = "") -> str:
    """获取环境变量 / Get an environment variable."""
    import os
    value = os.environ.get(key, default)
    return value if value else f"[env_get] '{key}' not set"


# ── v1.1 APIs ──


def file_exists(path: str) -> bool:
    """检查文件或目录是否存在 / Check if a file or directory exists."""
    return Path(path).exists()


def file_copy(src: str, dst: str) -> str:
    """复制文件 / Copy a file."""
    import shutil
    try:
        dest = shutil.copy2(src, dst)
        return str(Path(dest).resolve())
    except Exception as e:
        raise PluginError(f"file_copy failed: {e}")


def file_move(src: str, dst: str) -> str:
    """移动或重命名文件 / Move or rename a file."""
    import shutil
    try:
        dest = shutil.move(src, dst)
        return str(Path(dest).resolve())
    except Exception as e:
        raise PluginError(f"file_move failed: {e}")


def mkdir(path: str) -> str:
    """创建目录（含父目录）/ Create a directory (including parents)."""
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return str(p.resolve())
    except Exception as e:
        raise PluginError(f"mkdir failed: {e}")


def rm(path: str) -> str:
    """删除文件或空目录 / Remove a file or empty directory."""
    p = Path(path)
    try:
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            p.rmdir()
        else:
            return f"[rm] Not found: {path}"
        return f"[rm] Deleted: {p}"
    except Exception as e:
        return f"[rm error] {e}"


def path_join(*parts: str) -> str:
    """跨平台路径拼接 / Cross-platform path join."""
    return str(Path(*parts))


def base64_encode(text: str) -> str:
    """Base64 编码 / Encode text to Base64."""
    import base64
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def base64_decode(text: str) -> str:
    """Base64 解码 / Decode Base64 to text."""
    import base64
    try:
        return base64.b64decode(text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        return f"[base64_decode error] {e}"


def hash_file(path: str, algorithm: str = "sha256") -> str:
    """计算文件哈希 / Compute file hash (md5, sha1, sha256, sha512)."""
    import hashlib
    try:
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"[hash_file error] {e}"


def csv_parse(text: str, delimiter: str = ",") -> str:
    """解析 CSV 文本为 JSON / Parse CSV text to JSON array."""
    import csv
    import io
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = [dict(row) for row in reader]
        return _json.dumps(rows, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[csv_parse error] {e}"


def csv_stringify(data: str, delimiter: str = ",") -> str:
    """将 JSON 数组转为 CSV 文本 / Convert JSON array string to CSV."""
    import csv
    import io
    try:
        rows = _json.loads(data)
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
    except Exception as e:
        return f"[csv_stringify error] {e}"


def strftime(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化当前时间 / Format current datetime."""
    return _datetime.now().strftime(format_str)


def dict_keys(data: str) -> str:
    """获取 JSON 对象的所有键 / Get all keys of a JSON object."""
    try:
        obj = _json.loads(data)
        if isinstance(obj, dict):
            return _json.dumps(list(obj.keys()), ensure_ascii=False)
        return "[dict_keys error] Input is not a JSON object"
    except Exception as e:
        return f"[dict_keys error] {e}"


def dict_get(data: str, key: str, default: str = "") -> str:
    """从 JSON 对象中安全取值 / Safely get a value from a JSON object."""
    try:
        obj = _json.loads(data)
        if isinstance(obj, dict):
            value = obj.get(key, default)
            if isinstance(value, (dict, list)):
                return _json.dumps(value, ensure_ascii=False, indent=2)
            return str(value)
        return default
    except Exception:
        return default


def http_put(url: str, data: str = "", headers: str = "", timeout: int = 30) -> str:
    """发送 PUT 请求 / Send a PUT request."""
    import httpx
    try:
        parsed_headers = _json.loads(headers) if headers else None
        body = None
        if data:
            try:
                body = _json.loads(data)
            except _json.JSONDecodeError:
                body = data
        r = httpx.put(url, json=body if isinstance(body, (dict, list)) else None,
                      content=body if isinstance(body, str) else None,
                      headers=parsed_headers, timeout=timeout, follow_redirects=True)
        if "application/json" in r.headers.get("content-type", ""):
            return _json.dumps(r.json(), ensure_ascii=False, indent=2)
        return r.text[:5000]
    except Exception as e:
        return f"[http_put error: {e}]"


def http_delete(url: str, headers: str = "", timeout: int = 30) -> str:
    """发送 DELETE 请求 / Send a DELETE request."""
    import httpx
    try:
        parsed_headers = _json.loads(headers) if headers else None
        r = httpx.delete(url, headers=parsed_headers or None, timeout=timeout, follow_redirects=True)
        if "application/json" in r.headers.get("content-type", ""):
            return _json.dumps(r.json(), ensure_ascii=False, indent=2)
        return r.text[:5000] or "(empty response)"
    except Exception as e:
        return f"[http_delete error: {e}]"


def pwd() -> str:
    """获取当前工作目录 / Get current working directory."""
    import os
    return os.getcwd()


# ── v1.2 APIs: extensibility ──


# ── Regex ──

def re_search(pattern: str, text: str) -> str:
    """正则搜索，返回第一个匹配 / Regex search, return first match or empty."""
    import re
    try:
        m = re.search(pattern, text)
        if m:
            result = {"match": m.group(0), "groups": list(m.groups()), "span": list(m.span())}
            if m.groupdict():
                result["named"] = m.groupdict()
            return _json.dumps(result, ensure_ascii=False)
        return "(no match)"
    except re.error as e:
        return f"[re_search error] Invalid pattern: {e}"


def re_findall(pattern: str, text: str) -> str:
    """正则查找所有匹配 / Regex find all matches, return JSON array."""
    import re
    try:
        matches = re.findall(pattern, text)
        return _json.dumps(matches, ensure_ascii=False, indent=2)
    except re.error as e:
        return f"[re_findall error] Invalid pattern: {e}"


def re_replace(pattern: str, replacement: str, text: str) -> str:
    """正则替换 / Regex replace (sub)."""
    import re
    try:
        result, count = re.subn(pattern, replacement, text)
        return _json.dumps({"result": result, "replacements": count}, ensure_ascii=False)
    except re.error as e:
        return f"[re_replace error] Invalid pattern: {e}"


# ── Template ──

def template_render(template: str, variables: str) -> str:
    """模板渲染：{{var}} 替换 / Render template: replace {{var}} with values.

    variables 应为 JSON 对象字符串: '{"name": "World", "count": 42}'.
    """
    import re as _re
    try:
        vars_dict = _json.loads(variables)
        if not isinstance(vars_dict, dict):
            return "[template_render error] variables must be a JSON object"
    except _json.JSONDecodeError as e:
        return f"[template_render error] Invalid JSON: {e}"

    def _replace(m):
        key = m.group(1).strip()
        return str(vars_dict.get(key, m.group(0)))

    return _re.sub(r"\{\{\s*(\w+)\s*\}\}", _replace, template)


# ── SQLite ──

def db_query(db_path: str, sql: str, params: str = "[]") -> str:
    """执行 SQL 查询并返回 JSON 结果 / Execute a SELECT query, return JSON array.

    params: JSON 数组字符串，如 '["value", 42]'.
    """
    import sqlite3
    try:
        p = _json.loads(params) if params else []
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, p)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return _json.dumps(rows, ensure_ascii=False, indent=2)
    except sqlite3.Error as e:
        return f"[db_query error] {e}"
    except Exception as e:
        return f"[db_query error] {e}"


def db_execute(db_path: str, sql: str, params: str = "[]") -> str:
    """执行 SQL（INSERT/UPDATE/DELETE/CREATE）/ Execute non-SELECT SQL.

    params: JSON 数组字符串，如 '["value", 42]'.
    """
    import sqlite3
    try:
        p = _json.loads(params) if params else []
        conn = sqlite3.connect(db_path)
        conn.execute(sql, p)
        conn.commit()
        rowcount = conn.total_changes
        conn.close()
        return _json.dumps({"status": "ok", "rows_affected": rowcount}, ensure_ascii=False)
    except sqlite3.Error as e:
        return f"[db_execute error] {e}"
    except Exception as e:
        return f"[db_execute error] {e}"


# ── Archive ──

def zip_create(source_dir: str, output_path: str) -> str:
    """创建 ZIP 压缩包 / Create a ZIP archive from a directory."""
    import shutil
    try:
        p = Path(output_path)
        base = str(Path(source_dir).resolve())
        shutil.make_archive(str(p.with_suffix("")), "zip", base)
        return str(p.resolve())
    except Exception as e:
        return f"[zip_create error] {e}"


def zip_extract(zip_path: str, dest_dir: str) -> str:
    """解压 ZIP 文件 / Extract a ZIP archive."""
    import shutil
    try:
        shutil.unpack_archive(zip_path, dest_dir)
        return str(Path(dest_dir).resolve())
    except Exception as e:
        return f"[zip_extract error] {e}"


# ── Clipboard ──

def clipboard_read() -> str:
    """读取系统剪贴板 / Read system clipboard text."""
    try:
        import subprocess
        import os as _os
        if _os.name == "nt":
            r = subprocess.run(["powershell", "-Command", "Get-Clipboard"],
                             capture_output=True, text=True, timeout=5)
            return r.stdout.rstrip("\n") or "(empty)"
        else:
            # macOS
            r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return r.stdout.rstrip("\n") or "(empty)"
            # Linux
            for cmd in [["xclip", "-o", "-selection", "clipboard"],
                       ["wl-paste"]]:
                try:
                    r2 = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if r2.returncode == 0:
                        return r2.stdout.rstrip("\n") or "(empty)"
                except FileNotFoundError:
                    continue
            return "[clipboard_read] No clipboard tool found (install xclip or wl-clipboard)"
    except Exception as e:
        return f"[clipboard_read error] {e}"


def clipboard_write(text: str) -> str:
    """写入系统剪贴板 / Write text to system clipboard."""
    try:
        import subprocess
        import os as _os
        if _os.name == "nt":
            r = subprocess.run(
                ["powershell", "-Command", f"Set-Clipboard -Value {text!r}"],
                capture_output=True, text=True, timeout=5,
            )
            return "Copied to clipboard" if r.returncode == 0 else f"[error] {r.stderr}"
        else:
            for cmd_with_input in [
                (["pbcopy"], text),
                (["xclip", "-selection", "clipboard"], text),
                (["wl-copy"], text),
            ]:
                try:
                    r = subprocess.run(cmd_with_input[0], input=cmd_with_input[1],
                                     capture_output=True, text=True, timeout=5)
                    if r.returncode == 0:
                        return "Copied to clipboard"
                except FileNotFoundError:
                    continue
            return "[clipboard_write] No clipboard tool found"
    except Exception as e:
        return f"[clipboard_write error] {e}"


# ── Random ──

def random_int(a: int, b: int) -> int:
    """生成随机整数 [a, b] / Generate a random integer in [a, b]."""
    import random
    return random.randint(a, b)


def random_choice(data: str) -> str:
    """从 JSON 数组中随机选一个 / Pick a random element from a JSON array."""
    import random
    try:
        arr = _json.loads(data)
        if isinstance(arr, list) and arr:
            return str(random.choice(arr))
        return "[random_choice error] Input must be a non-empty JSON array"
    except _json.JSONDecodeError as e:
        return f"[random_choice error] {e}"


def random_shuffle(data: str) -> str:
    """随机打乱 JSON 数组 / Shuffle a JSON array randomly."""
    import random
    try:
        arr = _json.loads(data)
        if isinstance(arr, list):
            random.shuffle(arr)
            return _json.dumps(arr, ensure_ascii=False, indent=2)
        return "[random_shuffle error] Input must be a JSON array"
    except _json.JSONDecodeError as e:
        return f"[random_shuffle error] {e}"


# ── Config (TOML) ──

def load_toml(path: str) -> str:
    """读取 TOML 配置文件 / Read a TOML config file, return JSON."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return "[load_toml error] tomli/tomllib not installed (pip install tomli)"
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        return _json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[load_toml error] {e}"


def save_toml(path: str, data: str) -> str:
    """写入 TOML 配置文件 / Write a TOML config file (data is JSON string)."""
    try:
        import tomli_w
    except ImportError:
        return "[save_toml error] tomli-w not installed (pip install tomli-w)"
    try:
        obj = _json.loads(data)
        if not isinstance(obj, dict):
            return "[save_toml error] data must be a JSON object"
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tomli_w.dumps(obj), encoding="utf-8")
        return str(dest.resolve())
    except Exception as e:
        return f"[save_toml error] {e}"


# ── Diff ──

def diff_text(a: str, b: str, label_a: str = "original", label_b: str = "modified") -> str:
    """比较两段文本 / Compute unified diff between two strings."""
    import difflib
    diff = difflib.unified_diff(
        a.splitlines(keepends=True),
        b.splitlines(keepends=True),
        fromfile=label_a, tofile=label_b, lineterm="",
    )
    result = "".join(diff)
    return result if result else "(no differences)"


# ── Markdown ──

def markdown_to_text(md: str) -> str:
    """Markdown 转纯文本（去掉格式符号）/ Strip markdown formatting to plain text."""
    import re as _re
    text = md
    # Remove code blocks
    text = _re.sub(r"```[\s\S]*?```", "[code block]", text)
    # Remove inline code
    text = _re.sub(r"`([^`]+)`", r"\1", text)
    # Remove images
    text = _re.sub(r"!\[.*?\]\(.*?\)", "[image]", text)
    # Remove links, keep text
    text = _re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)
    # Remove headers markers
    text = _re.sub(r"^#{1,6}\s+", "", text, flags=_re.MULTILINE)
    # Remove bold/italic markers
    text = _re.sub(r"\*\*\*([^*]+)\*\*\*", r"\1", text)
    text = _re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = _re.sub(r"\*([^*]+)\*", r"\1", text)
    text = _re.sub(r"__([^_]+)__", r"\1", text)
    text = _re.sub(r"_([^_]+)_", r"\1", text)
    # Remove blockquote markers
    text = _re.sub(r"^>\s?", "", text, flags=_re.MULTILINE)
    # Remove horizontal rules
    text = _re.sub(r"^[-*_]{3,}\s*$", "", text, flags=_re.MULTILINE)
    # Collapse blank lines
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Network extras ──

def http_patch(url: str, data: str = "", headers: str = "", timeout: int = 30) -> str:
    """发送 PATCH 请求 / Send a PATCH request."""
    import httpx
    try:
        parsed_headers = _json.loads(headers) if headers else None
        body = None
        if data:
            try:
                body = _json.loads(data)
            except _json.JSONDecodeError:
                body = data
        r = httpx.patch(url, json=body if isinstance(body, (dict, list)) else None,
                        content=body if isinstance(body, str) else None,
                        headers=parsed_headers, timeout=timeout, follow_redirects=True)
        if "application/json" in r.headers.get("content-type", ""):
            return _json.dumps(r.json(), ensure_ascii=False, indent=2)
        return r.text[:5000]
    except Exception as e:
        return f"[http_patch error: {e}]"


def url_encode(text: str) -> str:
    """URL 编码 / URL-encode a string."""
    import urllib.parse
    return urllib.parse.quote(text)


def url_decode(text: str) -> str:
    """URL 解码 / URL-decode a string."""
    import urllib.parse
    return urllib.parse.unquote(text)
