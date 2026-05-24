# FluxLite

[github.com/SVolsa/fluxlite](https://github.com/SVolsa/fluxlite)

<details open>
<summary><b>中文</b> &nbsp;（点击切换到 English）</summary>

<br>

## 安装

```
pip install git+https://github.com/SVolsa/fluxlite.git
```

或本地安装：

```
git clone https://github.com/SVolsa/fluxlite.git
cd fluxlite
pip install -e .
```

要求：Python >= 3.9，OpenAI 兼容的 API Key。

## 快速上手

```bash
# 首次运行 — 设置向导
fluxlite --wizard

# 交互聊天
fluxlite

# 单次问答（不执行工具）
fluxlite "解释这段代码"

# 单次问答 + 自动执行工具
fluxlite --auto "跑测试并修复失败"
```

## 功能

| 功能 | 说明 |
|------|------|
| 对话 | 流式输出 + Markdown 渲染 |
| 工具 | 34 个内置工具：文件、代码、Git、搜索、终端、浏览器、HTTP |
| 插件 | `~/.fluxlite/plugins/` 放 JSON + Python 即可扩展 |
| 沙箱 | 文件操作隔离到临时目录，审核后应用或丢弃 |
| 会话 | 自动保存/恢复，支持搜索和导出 |
| 子代理 | `spawn_agents` 并行派发子任务 |
| 规划 | `task_planner` + `self_review` 先规划再自查 |
| Hooks | 工具执行前后触发自定义脚本 |
| MCP | 连接外部 MCP 服务器 |

## 内置工具 (34)

**文件**: `file_read` `file_write` `file_edit` `file_append` `file_delete` `file_list`
**代码**: `code_executor` `run_tests`
**Git**: `git_status` `git_diff` `git_log` `git_add` `git_commit`
**搜索**: `web_search` `grep_search` `glob_files`
**网络**: `http_request` `file_download` `web_scrape` `browser`
**终端**: `terminal`（持久会话）
**协作**: `spawn_agents` `task_planner` `self_review`
**记忆**: `memory_read` `memory_write` `rule_add` `rule_remove` `rule_list`
**系统**: `config_set` `mcp_call` `mcp_list` `hook_run` `hook_list`

## 命令

```
/help /clear /model /memory /rules /rule /think /compact /toolresult
/export /token /truncate /rewind /context /tools /lang /git
/autocommit /new /search /sessions /last /plan /mcp /hooks
/plugin /sandbox /diff /review /fix /pin /init /exit
```

- `/` 触发命令补全并显示描述
- `Ctrl+R` 搜索历史
- 行末 `\` 续行
- `/s` → `/sessions`，`/q` → `/exit`（短别名）

## 配置

`~/.fluxlite/config.toml`：

```toml
[api]
key = "your-api-key"
base_url = "https://api.deepseek.com"
model = "deepseek-chat"

[app]
language = "zh"
timeout = 60
safe_mode = true
```

也支持环境变量：`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `TAVILY_API_KEY`。

## 项目上下文

项目根目录放置 `FLUXLITE.md`，启动时自动注入。用 `/init` 自动生成。也可添加 `.fluxlite/project_memory.md` 和 `INSTRUCTIONS.md`。

## 插件

见 [API.md](API.md)，中英双语文档 + 示例。

## 测试

```
pytest tests/ -v
```

## 许可

MIT

</details>

<details>
<summary><b>English</b> &nbsp;（click to switch to 中文）</summary>

<br>

## Install

```
pip install git+https://github.com/SVolsa/fluxlite.git
```

Or from local:

```
git clone https://github.com/SVolsa/fluxlite.git
cd fluxlite
pip install -e .
```

Requirements: Python >= 3.9, OpenAI-compatible API key.

## Quickstart

```bash
# First run — setup wizard
fluxlite --wizard

# Interactive chat
fluxlite

# One-shot (no tool execution)
fluxlite "explain this code"

# One-shot with auto tool execution
fluxlite --auto "run the tests and fix failures"
```

## Features

| Feature | Description |
| ------- | ----------- |
| Chat | Streaming output + Markdown rendering |
| Tools | 34 built-in: file ops, code exec, git, search, terminal, browser, HTTP |
| Plugins | Drop JSON + Python in `~/.fluxlite/plugins/` to extend |
| Sandbox | File ops isolated to temp dir; review then apply or discard |
| Sessions | Auto save/restore, search, and export |
| Sub-agents | `spawn_agents` for parallel subtask dispatch |
| Planner | `task_planner` + `self_review` toolchain |
| Hooks | Custom scripts triggered pre/post tool execution |
| MCP | Connect external MCP servers |

## Built-in Tools (34)

**Files**: `file_read` `file_write` `file_edit` `file_append` `file_delete` `file_list`
**Code**: `code_executor` `run_tests`
**Git**: `git_status` `git_diff` `git_log` `git_add` `git_commit`
**Search**: `web_search` `grep_search` `glob_files`
**Network**: `http_request` `file_download` `web_scrape` `browser`
**Terminal**: `terminal` (persistent session)
**Planning**: `spawn_agents` `task_planner` `self_review`
**Memory**: `memory_read` `memory_write` `rule_add` `rule_remove` `rule_list`
**System**: `config_set` `mcp_call` `mcp_list` `hook_run` `hook_list`

## Commands

```
/help /clear /model /memory /rules /rule /think /compact /toolresult
/export /token /truncate /rewind /context /tools /lang /git
/autocommit /new /search /sessions /last /plan /mcp /hooks
/plugin /sandbox /diff /review /fix /pin /init /exit
```

- `/` triggers command completion with descriptions
- `Ctrl+R` for history search
- End line with `\` to continue typing
- `/s` → `/sessions`, `/q` → `/exit` (short aliases)

## Config

`~/.fluxlite/config.toml`:

```toml
[api]
key = "your-api-key"
base_url = "https://api.deepseek.com"
model = "deepseek-chat"

[app]
language = "zh"
timeout = 60
safe_mode = true
```

Also reads environment variables: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `TAVILY_API_KEY`.

## Project Context

Place `FLUXLITE.md` in your project root to inject it into the system prompt on startup. Use `/init` to auto-generate. Also supports `.fluxlite/project_memory.md` and `INSTRUCTIONS.md`.

## Plugins

See [API.md](API.md) for bilingual API docs and examples.

## Tests

```
pytest tests/ -v
```

## License

MIT

</details>
