_LANG = "zh"

_STRINGS = {
    "zh": {
        "welcome": "欢迎使用 FluxLite",
        "tool_running": "正在执行: {name}",
        "tool_result": "工具执行结果",
        "error": "错误",
        "no_api_key": "未配置 API Key，请编辑 ~/.fluxlite/config.toml 进行设置",
        "no_tavily_key": "未配置 Tavily API Key，搜索功能将无法使用",
        "config_created": "配置文件已创建: {path}",
        "exit": "再见",
        "thinking": "思考中",
        "responding": "响应中",
        "processing": "处理中",
        "show_memory": "查看身份信息、记忆与规则",
        "truncated": "回答已被截断",
        "compact_done": "记忆压缩完成",
        "think_on": "推理模式已启用，推理过程将随回答显示",
        "think_off": "推理模式已禁用",
        "think_display_on": "推理过程持续显示",
        "think_display_off": "推理过程自动收起",
        "help_desc": "显示此帮助信息",
        "clear_desc": "清除屏幕",
        "model_desc": "切换 AI 模型",
        "think_desc": "管理推理模式 on/off/display",
        "compact_desc": "压缩记忆条目",
        "truncate_desc": "移除最近一条 AI 回答",
        "rule_desc": "添加一项注意事项",
        "tools_desc": "列出可用工具",
        "lang_desc": "切换语言 (zh/en)",
        "exit_desc": "退出程序",
        "toolresult_desc": "显示/隐藏工具返回值 on/off",
        "export_desc": "导出对话记录",
        "token_desc": "切换 Token 用量显示",
    },
    "en": {
        "welcome": "Welcome to FluxLite",
        "tool_running": "Running tool: {name}",
        "tool_result": "Tool result",
        "error": "Error",
        "no_api_key": "No API Key configured. Edit ~/.fluxlite/config.toml to set it",
        "no_tavily_key": "No Tavily API Key configured. Search will be unavailable",
        "config_created": "Config created: {path}",
        "exit": "Goodbye",
        "thinking": "Thinking",
        "responding": "Responding",
        "processing": "Processing",
        "show_memory": "View identity, memory and rules",
        "truncated": "Response truncated",
        "compact_done": "Memory compaction complete",
        "think_on": "Reasoning enabled, thought process will be displayed",
        "think_off": "Reasoning disabled",
        "think_display_on": "Reasoning display: persistent",
        "think_display_off": "Reasoning display: auto-collapse",
        "help_desc": "Display this help information",
        "clear_desc": "Clear the screen",
        "model_desc": "Switch AI model",
        "think_desc": "Manage reasoning mode on/off/display",
        "compact_desc": "Compact memory entries",
        "truncate_desc": "Remove the most recent AI response",
        "rule_desc": "Add a user rule",
        "tools_desc": "List available tools",
        "lang_desc": "Switch language (zh/en)",
        "exit_desc": "Exit the program",
        "toolresult_desc": "Toggle tool result display on/off",
        "export_desc": "Export conversation",
        "token_desc": "Toggle token usage display",
    },
}


def set_lang(lang: str):
    global _LANG
    if lang in _STRINGS:
        _LANG = lang


def get_lang() -> str:
    return _LANG


def _(key: str, **kwargs) -> str:
    text = _STRINGS.get(_LANG, {}).get(key, _STRINGS.get("zh", {}).get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


