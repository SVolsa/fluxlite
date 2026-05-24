# FluxLite Plugin API

> 插件开发文档 — 中英双语 / Plugin Development Docs (EN/CN)

---

## AI 速查卡 / AI Quick Reference

如果你是一个 AI，被要求为 FluxLite 编写插件，以下是全部必要信息：

**文件结构：** 在 `~/.fluxlite/plugins/<name>/` 下创建两个文件：
- `<name>.json` — 元数据 + 工具定义（见下方 JSON 格式）
- `<name>.py` — 每个工具一个函数

**处理函数规则：**
- 签名：`def handler(args: dict) -> str` — 接收一个 dict，返回一个字符串
- args 的 key 对应 JSON 中 `parameters` 定义的参数名
- 函数名必须与 JSON 中 `"name"` 字段完全一致
- 函数同步执行，不能是 async
- 工具自动命名为 `plugin_{插件名}_{函数名}`，不会与内置工具冲突
- 插件发现：启动时 FluxLite 自动扫描插件目录并导入

**API 导入方式：**
```python
from fluxlite.plugin_api import PluginError, format_result, read_file, write_file, ...
```

**错误处理：**
- 参数缺失/无效 → `raise PluginError("描述信息")`
- API 函数多数返回错误字符串（如 `"[http_get error: ...]"`），不会自动抛异常
- 未捕获的异常由插件管理器捕获，工具会标记为 BROKEN

**参数类型（JSON schema）：** `"string"` / `"number"` / `"boolean"`，加 `"optional": true` 表示可省略。

**输出格式化：** 用 `format_result(dict)` 返回结构化数据，LLM 能更好理解。

**可用的 44 个 API 函数：** 见下方完整参考。所有函数从 `fluxlite.plugin_api` 导入。

---

## 插件结构 / Plugin Structure

每个插件是 `~/.fluxlite/plugins/<name>/` 下的一个文件夹，包含两个文件：

| 文件 / File | 必须 | 用途 / Purpose |
| ----------- | ---- | ---------------- |
| `<name>.json` | 是 | 元数据 + 工具 schema 定义 |
| `<name>.py` | 是 | 处理函数实现 |

---

## JSON 元数据 / Plugin JSON

```json
{
  "name": "myplugin",
  "version": "1.0.0",
  "description": "Short description of this plugin",
  "author": "Your Name",
  "website": "",
  "tools": [
    {
      "name": "tool_name",
      "description": "What this tool does — shown to the LLM",
      "parameters": {
        "param1": { "type": "string", "desc": "Description of param1", "optional": true },
        "param2": { "type": "number", "desc": "Description of param2" }
      }
    }
  ]
}
```

### 元数据字段 / Metadata fields

| 字段 | 类型 | 必须 | 说明 |
| ---- | ---- | ---- | ---- |
| `name` | string | 是 | 插件名，必须和文件夹名一致 |
| `version` | string | 否 | 版本号 |
| `description` | string | 否 | 一行描述 |
| `author` | string | 否 | 作者 |
| `website` | string | 否 | 项目地址 |

### 工具 schema 字段 / Tool schema fields

| 字段 | 类型 | 必须 | 说明 |
| ---- | ---- | ---- | ---- |
| `name` | string | 是 | 对应 `.py` 文件中的函数名 |
| `description` | string | 否 | 给 LLM 看的工具描述 |
| `parameters` | object | 否 | 参数定义 |

### 参数字段 / Parameter fields

| 字段 | 类型 | 必须 | 说明 |
| ---- | ---- | ---- | ---- |
| `type` | string | 是 | `"string"` / `"number"` / `"boolean"` |
| `desc` | string | 否 | 参数描述 |
| `optional` | boolean | 否 | `true` 表示可省略 |

---

## Python 处理函数 / Python Handler

`.py` 文件导出处理函数。每个函数接收一个 `dict` 参数（工具的参数）。

```python
"""myplugin plugin — FluxLite"""
from fluxlite.plugin_api import PluginError, format_result


def tool_name(args: dict) -> str:
    """Do something useful."""
    param1 = args.get("param1", "default_value")
    return format_result({"result": param1})
```

### 规则 / Rules

1. **函数名**必须与 JSON 中的 `"name"` 完全一致
2. **签名**: `def handler(args: dict) -> str` — 接收一个 dict，返回字符串
3. **同步**: 不支持 async
4. **PluginAPI**: 使用 `from fluxlite.plugin_api import ...` 调用辅助函数
5. **错误处理**: 主动校验参数，预期错误抛出 `PluginError`，未预期异常由插件管理器捕获

---

## PluginAPI 参考 / PluginAPI Reference

所有函数从 `fluxlite.plugin_api` 导入。

---

### `PluginError`

```python
class PluginError(Exception):
    """插件错误基类 / Base exception for plugin-related errors."""
```

工具因输入无效或资源缺失而无法完成时抛出。插件管理器会捕获并返回友好的错误消息。

使用示例：

```python
if not path:
    raise PluginError("path is required")
```

---

### `format_result(data)`

```python
def format_result(data: dict | list | str) -> str
```

格式化返回值为 FluxLite 可读的字符串：

- `dict` 或 `list` → 格式化 JSON
- `str` → 原样返回

```python
return format_result({"status": "ok", "count": 42})
# → '{\n  "status": "ok",\n  "count": 42\n}'
```

---

### `read_file(path)`

```python
def read_file(path: str) -> str
```

读取文本文件内容。失败时抛出 `PluginError`。

---

### `write_file(path, content)`

```python
def write_file(path: str, content: str) -> str
```

将文本写入文件（自动创建父目录）。返回绝对路径。失败时抛出 `PluginError`。

---

### `run_command(command, timeout=30)`

```python
def run_command(command: str, timeout: int = 30) -> str
```

执行 shell 命令。返回 stdout+stderr 合并输出。非零退出码不会抛异常。

---

### `http_get(url, headers="", timeout=30)`

```python
def http_get(url: str, headers: str = "", timeout: int = 30) -> str
```

发送 GET 请求。headers 为 JSON 字符串，如 `'{"Authorization": "Bearer ..."}'`。
JSON 响应会自动格式化。文本响应截断至 5000 字符。

---

### `http_post(url, data="", headers="", timeout=30)`

> 新增于 v0.2 / New in v0.2

```python
def http_post(url: str, data: str = "", headers: str = "", timeout: int = 30) -> str
```

发送 POST 请求。data 如果是 dict/list 会自动 JSON 编码，文本则作为原始 body 发送。

```python
# 发送 JSON
http_post("https://api.example.com/data",
          data='{"key": "value"}',
          headers='{"Content-Type": "application/json"}')

# 发送文本
http_post("https://httpbin.org/post", data="hello")
```

---

### `grep(pattern, path=".", file_glob="")`

```python
def grep(pattern: str, path: str = ".", file_glob: str = "") -> str
```

在文件中搜索正则表达式。返回前 3000 字符匹配结果。`file_glob` 按 glob 过滤（如 `"*.py"`）。

---

### `json_parse(text)`

> 新增于 v0.2 / New in v0.2

```python
def json_parse(text: str) -> str
```

安全解析 JSON 字符串。返回格式化后的 JSON（成功）或错误信息（失败）。

```python
result = json_parse('{"name": "test", "count": 42}')
# → {
#     "name": "test",
#     "count": 42
#   }

result = json_parse("{bad json}")
# → [json_parse error] Invalid JSON: ...
```

---

### `load_json(path)`

> 新增于 v0.2 / New in v0.2

```python
def load_json(path: str) -> str
```

读取并解析 JSON 文件。返回格式化 JSON 或错误信息。

---

### `save_json(path, data)`

> 新增于 v0.2 / New in v0.2

```python
def save_json(path: str, data: str) -> str
```

将数据序列化为 JSON 并写入文件。data 应为 JSON 字符串。返回绝对路径。

```python
save_json("/tmp/config.json", '{"port": 8080, "debug": true}')
```

---

### `list_dir(path=".")`

> 新增于 v0.2 / New in v0.2

```python
def list_dir(path: str = ".") -> str
```

列出目录内容。目录项以 `/` 结尾。每行一个。

```
file1.txt
subdir/
script.py
```

---

### `uuid_gen()`

> 新增于 v0.2 / New in v0.2

```python
def uuid_gen() -> str
```

生成 UUID v4 字符串。适合生成唯一标识符。

```python
uuid_gen()  # → "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### `timestamp()`

> 新增于 v0.2 / New in v0.2

```python
def timestamp() -> str
```

获取当前 ISO 8601 格式时间戳。

```python
timestamp()  # → "2025-05-23T14:30:00.123456"
```

---

### `env_get(key, default="")`

> 新增于 v0.2 / New in v0.2

```python
def env_get(key: str, default: str = "") -> str
```

获取环境变量值。未设置时返回默认值或提示信息。

```python
home = env_get("HOME")
mode = env_get("APP_MODE", "production")
```

---

### `file_exists(path)`

> v1.1

```python
def file_exists(path: str) -> bool
```

检查文件或目录是否存在。返回布尔值。

---

### `file_copy(src, dst)`

> v1.1

```python
def file_copy(src: str, dst: str) -> str
```

复制文件。返回目标路径。失败时抛出 `PluginError`。

---

### `file_move(src, dst)`

> v1.1

```python
def file_move(src: str, dst: str) -> str
```

移动或重命名文件。返回目标路径。失败时抛出 `PluginError`。

---

### `mkdir(path)`

> v1.1

```python
def mkdir(path: str) -> str
```

创建目录（含父目录）。返回绝对路径。失败时抛出 `PluginError`。

---

### `rm(path)`

> v1.1

```python
def rm(path: str) -> str
```

删除文件或空目录。返回操作结果字符串。

---

### `path_join(*parts)`

> v1.1

```python
def path_join(*parts: str) -> str
```

跨平台路径拼接。`path_join("a", "b", "c")` → `"a/b/c"` (Unix) / `"a\\b\\c"` (Windows)。

---

### `hash_file(path, algorithm="sha256")`

> v1.1

```python
def hash_file(path: str, algorithm: str = "sha256") -> str
```

计算文件哈希。algorithm 可选 `md5`、`sha1`、`sha256`、`sha512`。返回十六进制字符串。

---

### `base64_encode(text)`

> v1.1

```python
def base64_encode(text: str) -> str
```

Base64 编码。

---

### `base64_decode(text)`

> v1.1

```python
def base64_decode(text: str) -> str
```

Base64 解码。失败时返回错误信息。

---

### `csv_parse(text, delimiter=",")`

> v1.1

```python
def csv_parse(text: str, delimiter: str = ",") -> str
```

解析 CSV 文本为 JSON 数组。首行作为列名。

---

### `csv_stringify(data, delimiter=",")`

> v1.1

```python
def csv_stringify(data: str, delimiter: str = ",") -> str
```

将 JSON 数组转为 CSV 文本。data 为 JSON 字符串。

---

### `strftime(format="%Y-%m-%d %H:%M:%S")`

> v1.1

```python
def strftime(format_str: str = "%Y-%m-%d %H:%M:%S") -> str
```

格式化当前时间。

---

### `dict_keys(data)`

> v1.1

```python
def dict_keys(data: str) -> str
```

提取 JSON 对象的所有 key，返回 JSON 数组。

---

### `dict_get(data, key, default="")`

> v1.1

```python
def dict_get(data: str, key: str, default: str = "") -> str
```

从 JSON 对象中安全取值。key 不存在时返回 default。

---

### `http_put(url, data="", headers="", timeout=30)`

> v1.1

```python
def http_put(url: str, data: str = "", headers: str = "", timeout: int = 30) -> str
```

发送 PUT 请求。用法同 `http_post`。

---

### `http_delete(url, headers="", timeout=30)`

> v1.1

```python
def http_delete(url: str, headers: str = "", timeout: int = 30) -> str
```

发送 DELETE 请求。

---

### `pwd()`

> v1.1

```python
def pwd() -> str
```

获取当前工作目录。

---

### `re_search(pattern, text)`

> v1.2

```python
def re_search(pattern: str, text: str) -> str
```

正则搜索，返回第一个匹配的 JSON（含 match/groups/span）。

---

### `re_findall(pattern, text)`

> v1.2

```python
def re_findall(pattern: str, text: str) -> str
```

正则查找所有匹配，返回 JSON 数组。

---

### `re_replace(pattern, replacement, text)`

> v1.2

```python
def re_replace(pattern: str, replacement: str, text: str) -> str
```

正则替换，返回 JSON（含 result/replacements 计数）。

---

### `template_render(template, variables)`

> v1.2

```python
def template_render(template: str, variables: str) -> str
```

模板渲染：将 `{{ var }}` 替换为 variables 中的值。variables 为 JSON 对象字符串。

```python
template_render("Hello {{ name }}", '{"name": "World"}')
# → "Hello World"
```

---

### `db_query(db_path, sql, params="[]")`

> v1.2

```python
def db_query(db_path: str, sql: str, params: str = "[]") -> str
```

执行 SQLite SELECT 查询。params 为 JSON 数组字符串。返回 JSON 数组。

```python
db_query("app.db", "SELECT * FROM users WHERE id = ?", '[42]')
```

---

### `db_execute(db_path, sql, params="[]")`

> v1.2

```python
def db_execute(db_path: str, sql: str, params: str = "[]") -> str
```

执行 SQLite 写操作（INSERT/UPDATE/DELETE/CREATE）。返回 rows_affected。

---

### `zip_create(source_dir, output_path)`

> v1.2

```python
def zip_create(source_dir: str, output_path: str) -> str
```

将目录打包为 ZIP。

---

### `zip_extract(zip_path, dest_dir)`

> v1.2

```python
def zip_extract(zip_path: str, dest_dir: str) -> str
```

解压 ZIP 文件到目标目录。

---

### `clipboard_read()`

> v1.2

```python
def clipboard_read() -> str
```

读取系统剪贴板文本。跨平台（Windows/macOS/Linux）。

---

### `clipboard_write(text)`

> v1.2

```python
def clipboard_write(text: str) -> str
```

写入文本到系统剪贴板。跨平台。

---

### `random_int(a, b)` / `random_choice(data)` / `random_shuffle(data)`

> v1.2

```python
def random_int(a: int, b: int) -> int
def random_choice(data: str) -> str   # data 为 JSON 数组
def random_shuffle(data: str) -> str  # data 为 JSON 数组
```

随机数工具。

---

### `load_toml(path)` / `save_toml(path, data)`

> v1.2

```python
def load_toml(path: str) -> str       # 返回 JSON
def save_toml(path: str, data: str) -> str  # data 为 JSON 字符串
```

TOML 配置文件读写。需安装 `tomli` / `tomli-w`。

---

### `diff_text(a, b, label_a, label_b)`

> v1.2

```python
def diff_text(a: str, b: str, label_a: str = "original", label_b: str = "modified") -> str
```

比较两段文本，返回 unified diff。

---

### `markdown_to_text(md)`

> v1.2

```python
def markdown_to_text(md: str) -> str
```

去掉 Markdown 格式符号，提取纯文本。

---

### `http_patch(url, data="", headers="", timeout=30)`

> v1.2

```python
def http_patch(url: str, data: str = "", headers: str = "", timeout: int = 30) -> str
```

发送 PATCH 请求。

---

### `url_encode(text)` / `url_decode(text)`

> v1.2

```python
def url_encode(text: str) -> str
def url_decode(text: str) -> str
```

URL 编码/解码。

---

## 插件管理命令 / Management Commands

通过 `/plugin` 使用：

| 命令 | 说明 |
| ---- | ---- |
| `/plugin list` | 列出所有插件及状态 |
| `/plugin info <name>` | 显示插件详情和工具 |
| `/plugin enable <name>` | 启用插件 |
| `/plugin disable <name>` | 禁用插件 |
| `/plugin create <name>` | 创建新插件脚手架 |
| `/plugin reload` | 重新扫描插件目录 |

---

## 工具命名 / Tool Naming

插件工具自动添加前缀以避免与内置工具冲突：

```
plugin_{name}_{func_name}
```

例如，`greeter` 插件中的 `hello` 工具变为 `plugin_greeter_hello`。

---

## 状态持久化 / State Persistence

插件启用/禁用状态保存在 `~/.fluxlite/plugin_state.json`。禁用的插件不会暴露给 LLM。

---

## 加载错误 / Load Errors

插件加载失败时，`/plugin list` 会显示 `[error]` 状态和错误信息。修复后执行 `/plugin reload` 重新加载。

常见错误：

| 错误 | 原因 |
| ---- | ---- |
| Invalid JSON | `.json` 文件语法错误 |
| No tools defined | JSON 中 `"tools"` 为空或缺失 |
| Missing `<name>.py` | 找不到处理函数文件 |
| Failed to import `<name>.py` | Python 语法错误或 import 失败 |
| Handler 'xxx' not found | JSON 中的函数名在 `.py` 中不存在 |
| 'xxx' is not callable | 该名称存在但不是函数 |

---

## 完整示例 / Complete Example

### `~/.fluxlite/plugins/textutils/textutils.json`

```json
{
  "name": "textutils",
  "version": "1.0.0",
  "description": "Text file utilities — word count and search",
  "author": "FluxLite",
  "website": "",
  "tools": [
    {
      "name": "word_count",
      "description": "Count words, lines, and characters in a text file",
      "parameters": {
        "path": { "type": "string", "desc": "Path to the text file" }
      }
    },
    {
      "name": "find_lines",
      "description": "Find lines in a file matching a substring or regex",
      "parameters": {
        "path": { "type": "string", "desc": "Path to the text file" },
        "pattern": { "type": "string", "desc": "Search pattern" },
        "max_results": { "type": "number", "desc": "Max results to return", "optional": true }
      }
    }
  ]
}
```

### `~/.fluxlite/plugins/textutils/textutils.py`

```python
"""textutils plugin — FluxLite"""
import re
from fluxlite.plugin_api import PluginError, format_result, read_file


def word_count(args: dict) -> str:
    """Count words, lines, and characters in a file."""
    path = args.get("path")
    if not path:
        raise PluginError("path is required")

    content = read_file(path)
    lines = content.splitlines()
    words = len(content.split())
    chars = len(content)

    return format_result({
        "file": path,
        "lines": len(lines),
        "words": words,
        "characters": chars,
    })


def find_lines(args: dict) -> str:
    """Find lines matching a pattern."""
    path = args.get("path")
    pattern = args.get("pattern")
    if not path or not pattern:
        raise PluginError("path and pattern are required")

    content = read_file(path)
    max_results = int(args.get("max_results", 50))
    matches = []
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(pattern, line):
            matches.append(f"{i}: {line}")
            if len(matches) >= max_results:
                break

    return format_result({
        "file": path,
        "pattern": pattern,
        "matches": len(matches),
        "lines": matches,
    })
```

---

## 开发建议 / Tips

- **工具描述**要清晰具体 — LLM 据此决定调用哪个工具
- 参数可省略时使用 `"optional": true`，LLM 会推断默认值
- 使用 `format_result(dict)` 返回结构化数据，LLM 可以读取并决定显示内容
- 每个 handler 开头校验必要参数，不满足时抛出 `PluginError`
- 一个插件可包含多个相关工具（如 `create`、`read`、`delete`）
- 使用 `timestamp()` + `uuid_gen()` 生成日志/记录的唯一标识
- 复杂数据操作优先用 `load_json` / `save_json` 而非手动 `read_file` + `json_parse`
- 持久化存储用 `db_query` / `db_execute`（SQLite），比读写 JSON 文件更适合多记录查询
- 生成配置文件用 `template_render` + `write_file` 组合
- 处理用户输入文本用 `re_search` / `re_findall` / `re_replace` 正则工具链
- 跨平台剪贴板操作用 `clipboard_read` / `clipboard_write`
