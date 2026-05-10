# FluxLite

[English](#english) | [中文](#chinese)

---

<a id="chinese"></a>

# FluxLite — 终端 AI Agent

运行在终端里的 AI Agent，支持多模型、记忆、工具调用和推理展示。纯终端界面，不挑浏览器。

## 特点

- **轻量** — 纯终端运行，没有 Electron，没有浏览器，没有 GUI 框架。启动快，内存占用低
- **数据本地化** — 对话记录、记忆、配置全部存在 `~/.fluxlite/`，不依赖第三方云服务
- **API Key 加密** — 使用 Fernet 加密存储，密钥由机器特征派生，文件权限自动锁定
- **直连 API** — 直接调用 AI 提供商接口，不走中间代理
- **多模型切换** — DeepSeek、OpenAI、Anthropic Claude、OpenRouter、Groq，一个命令切过去，不用重启
- **推理过程可见** — DeepSeek 和 Claude 能展示思考过程，灰色文字实时显示
- **终端该有的都有** — 逐字流式输出、等待动画、多行编辑（Enter 发送，Esc+Enter 换行）、Ctrl+C 截断
- **轻量 Agent** — 工具调用、规则系统、记忆管理，AI 能操作文件、执行代码、搜索网页
- **上路就能用** — 首次启动走一遍向导，填完 API Key 就能聊

## 安装

### 环境要求

- Python >= 3.9
- 终端支持 UTF-8（Windows Terminal / macOS Terminal / Linux 均可）

### 方式一：pip 安装

```bash
git clone https://github.com/SVolsa/fluxlite
cd fluxlite
pip install .
```

### 方式二：直接运行

```bash
pip install -r requirements.txt
python -m fluxlite
```

安装后终端中输入 `fluxlite` 即可启动。

## 首次启动

首次运行会自动进入设置向导：

```
  ─ Identity Setup ─────────────────────
  What should I call you? > Volsa
  What would you like to name me? > FLux
  Describe my personality (optional) > 专业
```

向导步骤：

1. **身份设置** — 你的称呼、AI 名称、AI 性格（存储在 `memory.json`）
2. **AI 提供商** — DeepSeek / OpenAI / Anthropic Claude / OpenRouter / Groq 预设
3. **API Key** — 输入密钥（自动加密后存储）
4. **模型选择** — 自动填充对应提供商的主流模型
5. **搜索配置** — 可选配置 Tavily 网络搜索

### 手动配置

配置文件位于 `~/.fluxlite/config.toml`：

```toml
[api]
key = "gAAAAAB..."
base_url = "https://api.deepseek.com"
model = "deepseek-chat"

[app]
language = "zh"
timeout = 60
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `/help` | 显示所有命令 |
| `/model` | 切换 AI 模型 |
| `/think on` | 启用推理模式 |
| `/think off` | 禁用推理模式 |
| `/think display` | 推理过程持续显示 |
| `/think display off` | 推理过程自动收起 |
| `/toolresult on` | 显示工具执行返回值 |
| `/toolresult off` | 隐藏工具返回值（默认） |
| `/memory` | 查看身份信息、记忆条目、规则列表 |
| `/compact` | 压缩记忆条目 |
| `/truncate` | 移除最近一条 AI 回答 |
| `/rule <内容>` | 添加一条用户规则 |
| `/token` | 切换 Token 用量显示（in/out/total） |
| `/export` | 导出对话记录为 md 文件 |
| `/tools` | 列出所有可用工具 |
| `/clear` | 清除屏幕 |
| `/lang` | 切换语言 zh/en |
| `/exit` | 退出程序 |

### 输入操作

| 按键 | 行为 |
|------|------|
| `Enter` | 提交发送 |
| `Esc` → `Enter` | 换行（多行输入） |
| `↑ ↓ ← →` | 光标移动 |
| `Ctrl+C` | 截断 AI 当前回答 |
| `粘贴文本` | 自动保留格式和换行 |

## 安全

- **API Key 加密** — 使用 `cryptography.fernet` 对称加密
- **密钥文件保护** — `.fluxkey` 设置为仅当前用户可读写（Windows `icacls` / Unix `chmod 600`）
- **数据本地** — 配置、记忆、对话历史全部存储在 `~/.fluxlite/`

## 记忆系统

记忆存储在 `~/.fluxlite/memory.json`：

```json
{
  "identity": {
    "name": "Flux",
    "personality": "专业",
    "user_name": "Volsa",
    "created_at": "2026-05-10T17:30:00"
  },
  "memories": [
    { "id": "20260510173001", "content": "用户喜欢简洁的回答", "created_at": "..." }
  ],
  "rules": [
    "回答尽量简洁",
    "不要使用 emoji"
  ]
}
```

- AI 可通过 `memory_write` / `memory_read` 工具自主管理记忆
- `/compact` 压缩记忆条目
- `/rule <内容>` 添加规则

## 推理过程显示

支持显示 AI 的思考过程（灰色文字）：

| 模式 | 指令 | 效果 |
|------|------|------|
| 关闭 | `/think off` | 不显示推理过程（默认） |
| 可见 | `/think on` | 推理过程持续显示 |
| 收起 | `/think display off` 或 `/think display` | 推理过程在回答结束后自动隐藏 |

支持的模型：
- **DeepSeek** — 原生 `reasoning_content` 字段
- **Anthropic Claude Sonnet/Opus** — `thinking` content block

## Token 用量

`/token` 开关控制是否显示 Token 用量。开启后每条回答末尾显示：

```
│ in: 123  out: 456  total: 579
```

支持 OpenAI 格式（`prompt_tokens`/`completion_tokens`）和 Anthropic 格式（`input_tokens`/`output_tokens`）。

## 对话持久化

- 对话自动保存到 `~/.fluxlite/history/latest.json`
- 重启后自动恢复上一次对话（含历史消息）
- `/export` 导出为 Markdown 文件

## 故障恢复

- **自动重试** — API 请求失败自动重试最多 3 次，间隔 1 秒
- **截断回答** — 流式输出时 Ctrl+C 即时截断
- **错误提示** — 连接失败、API 错误等均有中文/英文提示

## 项目结构

```
```
fluxlite/                   # 项目根目录
│
├── pyproject.toml          # 项目元信息与依赖
├── LICENSE                 # MIT 许可证
├── README.md               # 本文档
├── .gitignore              # Git 忽略规则
│
├── fluxlite/               # Python 包目录
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py              # 主聊天循环、流式输出
│   ├── main.py             # CLI 入口、参数解析
│   ├── commands.py         # 斜杠命令处理、状态管理
│   ├── console.py          # 终端输入
│   ├── wizard.py           # 首次设置向导
│   ├── config.py           # TOML 配置读写 + 加解密
│   ├── memory.py           # 三段式记忆系统
│   ├── i18n.py             # 中英文国际化
│   ├── startup.py          # 启动 ASCII Logo
│   ├── styles.py           # Rich 主题色与样式
│   │
│   ├── provider/           # AI 提供商适配
│   │   ├── __init__.py     # Provider 工厂
│   │   ├── base.py         # 抽象 Provider 基类
│   │   ├── openai_compat.py     # OpenAI 兼容 API（DeepSeek/OpenAI/Groq）
│   │   └── anthropic.py         # Anthropic Claude API
│   │
│   └── tools/              # 工具模块
│       ├── registry.py     # 工具注册与执行引擎
│       ├── file_ops.py     # 文件读写/编辑/删除/列表
│       ├── code_exec.py    # Python/Bash 代码执行
│       └── web_search.py   # Tavily 网络搜索
│
└── tests/                  # 测试
    ├── __init__.py
    ├── conftest.py         # 测试共享夹具
    ├── test_config.py      # 配置加解密测试
    ├── test_memory.py      # 记忆读写测试
    └── test_provider.py    # Provider 工厂测试
```

## 数据文件

| 文件 | 说明 |
|------|------|
| `~/.fluxlite/config.toml` | API 配置、模型、语言设置 |
| `~/.fluxlite/.fluxkey` | 加密密钥文件 |
| `~/.fluxlite/memory.json` | 身份、记忆、规则 |
| `~/.fluxlite/history/latest.json` | 最新对话历史 |

## 测试

```bash
pip install pytest
pytest tests/
```

当前 30 个测试覆盖：配置加解密、记忆读写、Provider 工厂。

## 开源协议

MIT
## 声明

纯娱乐开发，写着玩的awa
---

<a id="english"></a>

# FluxLite — Terminal AI Agent

Runs in your terminal. No browser, no Electron, no GUI framework. Just the AI.

## Why FluxLite

- **Lightweight** — Native terminal app. Starts fast, low memory footprint
- **Local storage** — Chats, memories, config all live in `~/.fluxlite/`. No cloud dependency
- **API key encryption** — Encrypted with Fernet using a machine-derived key. Key file permissions are locked automatically
- **Direct API access** — Calls AI providers directly. No proxy, no middleman
- **Multi-model** — DeepSeek, OpenAI, Claude, OpenRouter, Groq. Switch with one command, no restart
- **Reasoning visibility** — DeepSeek and Claude can display their reasoning in real time as grey text
- **Terminal-native** — Character-by-character streaming, spinner animations, multi-line input (Enter to send, Esc+Enter for newline), Ctrl+C to truncate
- **Tool-capable** — File operations, code execution, web search. AI can use tools autonomously based on your rules
- **Quick start** — First run launches a setup wizard. Enter your API key and start chatting

## Install

### You'll need

- Python >= 3.9
- A terminal that does UTF-8 (Windows Terminal, macOS Terminal, Linux — all work)

### Quick install

```bash
git clone https://github.com/SVolsa/fluxlite
cd fluxlite
pip install .
```

### Or just run it

```bash
pip install -r requirements.txt
python -m fluxlite
```

After install, type `fluxlite` anywhere and you're in.

## First Time

The wizard walks you through everything:

```
  ─ Identity Setup ─────────────────────
  What should I call you? > Alice
  What would you like to name me? > Nova
  Describe my personality (optional) > Friendly and concise
```

Steps:

1. **Identity** — Tell it your name, give it a name, describe its personality (saved in `memory.json`)
2. **Pick a provider** — DeepSeek, OpenAI, Claude, OpenRouter, or Groq
3. **Enter your API key** — Gets encrypted before saving
4. **Choose a model** — Picks a sensible default for your provider
5. **Web search** — Optional Tavily setup

### Manual config

File is at `~/.fluxlite/config.toml`. API keys are stored encrypted:

```toml
[api]
key = "gAAAAAB..."  # not your plaintext key
base_url = "https://api.deepseek.com"
model = "deepseek-chat"

[app]
language = "en"
timeout = 60
```

## Commands

| Command | What it does |
|---------|-------------|
| `/help` | Lists all commands |
| `/model` | Switch models (shows presets for your provider) |
| `/think on` | Show AI's reasoning process |
| `/think off` | Hide reasoning (default) |
| `/think display` | Keep reasoning visible |
| `/think display off` | Auto-hide reasoning after reply |
| `/toolresult on` | Show what tools returned |
| `/toolresult off` | Hide tool output (default) |
| `/memory` | View identity, memories, rules |
| `/compact` | Squash memory entries together |
| `/truncate` | Delete the last AI response |
| `/rule <text>` | Add a rule for the AI |
| `/token` | Show/hide token counts |
| `/export` | Save conversation as a .md file |
| `/tools` | List every available tool |
| `/clear` | Clear the screen |
| `/lang` | Switch between zh and en |
| `/exit` | Leave |

### While typing

| Key | What happens |
|-----|-------------|
| `Enter` | Sends your message |
| `Esc` then `Enter` | Adds a newline |
| Arrow keys | Move cursor around |
| `Ctrl+C` | Stops the AI mid-response |
| Paste | Works, keeps your formatting |

## Security

- **API key encryption** — Uses `cryptography.fernet`. Key is derived from your machine's hostname
- **Key file locked down** — `.fluxkey` gets `icacls` treatment on Windows, `chmod 600` on Unix. Only you can read it
- **All local** — Config, memories, chat history. All in `~/.fluxlite/`. Nothing phones home

## Memory

Everything lives in `~/.fluxlite/memory.json`:

```json
{
  "identity": {
    "name": "Nova",
    "personality": "Friendly and concise",
    "user_name": "Alice",
    "created_at": "2026-05-10T17:30:00"
  },
  "memories": [
    { "id": "20260510173001", "content": "User prefers concise answers", "created_at": "..." }
  ],
  "rules": [
    "Keep answers brief",
    "No emoji"
  ]
}
```

- AI can write and read memories on its own using `memory_write` / `memory_read`
- `/compact` merges old memories
- `/rule <text>` adds something for the AI to keep in mind

## Showing AI's Thoughts

When supported, the AI's internal reasoning appears in grey:

| Mode | Command | What you see |
|------|---------|-------------|
| Off | `/think off` | Nothing (default) |
| On | `/think on` | Reasoning stays above the answer |
| Collapsed | `/think display` | Reasoning disappears after the answer finishes |

Works with:
- **DeepSeek** — uses the `reasoning_content` field
- **Claude Sonnet/Opus** — uses the `thinking` content block

## Token Usage

Turn it on with `/token`. Each response will show:

```
│ in: 123  out: 456  total: 579
```

Understands both OpenAI's format (`prompt_tokens`/`completion_tokens`) and Anthropic's (`input_tokens`/`output_tokens`).

## Session Save & Restore

- Conversations get saved to `~/.fluxlite/history/latest.json` as you go
- Come back later and your last session picks up where it left off
- `/export` dumps the whole thing as Markdown

## When Things Go Wrong

- **Auto retry** — Failed API calls try again up to 3 times, one second apart
- **Cut it off** — Hit Ctrl+C during streaming to stop the AI mid-sentence
- **Errors in your language** — Messages show in Chinese or English depending on your setting

## Project Layout

```
fluxlite/                   # Project root
│
├── pyproject.toml          # Package metadata & deps
├── LICENSE                 # MIT license
├── README.md               # This file
├── .gitignore              # Git ignore rules
│
├── fluxlite/               # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py              # Main loop, streaming
│   ├── main.py             # Entry point, CLI args
│   ├── commands.py         # Slash commands, state
│   ├── console.py          # Input handling
│   ├── wizard.py           # Setup wizard
│   ├── config.py           # Config read/write + encryption
│   ├── memory.py           # Memory management
│   ├── i18n.py             # Chinese + English strings
│   ├── startup.py          # Logo on launch
│   ├── styles.py           # Colors, themes
│   │
│   ├── provider/           # AI provider adapters
│   │   ├── __init__.py     # Picks the right provider
│   │   ├── base.py         # Base class
│   │   ├── openai_compat.py     # DeepSeek, OpenAI, Groq, OpenRouter
│   │   └── anthropic.py         # Claude
│   │
│   └── tools/              # Tool modules
│       ├── registry.py     # Tool list, dispatch
│       ├── file_ops.py     # Read, write, edit, delete, list
│       ├── code_exec.py    # Run Python or Bash
│       └── web_search.py   # Tavily search
│
└── tests/                  # Tests
    ├── __init__.py
    ├── conftest.py         # Shared test setup
    ├── test_config.py      # Encryption round-trip
    ├── test_memory.py      # Memory save/load
    └── test_provider.py    # Provider detection
```

## Files

| File | What it is |
|------|-----------|
| `~/.fluxlite/config.toml` | API keys (encrypted), model, language |
| `~/.fluxlite/.fluxkey` | Your encryption key (locked to you) |
| `~/.fluxlite/memory.json` | Identity, memories, rules |
| `~/.fluxlite/history/latest.json` | Your most recent conversation |

## Tests

```bash
pip install pytest
pytest tests/
```

30 tests covering config encryption, memory operations, and provider selection.

## License

MIT

## Statement

Made for fun. Just messing around with code.