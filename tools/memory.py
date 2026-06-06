"""
Memory tool - 统一记忆系统
使用MemoryManager作为唯一实现
"""

import json
from core.memory_manager import get_memory_manager


def read_memory() -> dict:
    """
    读取用户记忆，包括喜好、习惯、历史对话摘要。
    用这个工具来了解用户的偏好，让回答更个性化。
    """
    manager = get_memory_manager()
    user_info = manager.get_user_info()
    return {
        "content": user_info,
        "is_error": False
    }


def update_memory(category: str, key: str, value: str) -> dict:
    """
    更新用户记忆。当发现用户的新习惯、喜好、或重要信息时调用。

    category: "preferences" / "habits" / "personal_notes" / "user_name" / "conversation_history"
    key: 要更新的字段名
    value: 新的值（如果是列表类型，会追加而非覆盖）
    """
    manager = get_memory_manager()
    memory = manager.memory

    if category == "user_name":
        memory["user_name"] = value
    elif category == "personal_notes":
        from datetime import datetime
        note = f"[{datetime.now().strftime('%m-%d %H:%M')}] {value}"
        memory.setdefault("personal_notes", []).append(note)
        # 只保留最近20条
        memory["personal_notes"] = memory["personal_notes"][-20:]
    elif category in ("preferences", "habits"):
        if key in memory.get(category, {}):
            if isinstance(memory[category][key], list):
                if value not in memory[category][key]:
                    memory[category][key].append(value)
            else:
                memory[category][key] = value
        else:
            memory.setdefault(category, {})[key] = value
    elif category == "conversation_history":
        if key == "topics_discussed":
            topics = memory.setdefault("conversation_history", {}).setdefault("topics_discussed", [])
            if value not in topics:
                topics.append(value)
                memory["conversation_history"]["topics_discussed"] = topics[-30:]
        elif key == "tools_used":
            tools = memory.setdefault("conversation_history", {}).setdefault("tools_used", {})
            tools[value] = tools.get(value, 0) + 1
        else:
            memory.setdefault("conversation_history", {})[key] = value

    # 更新最后对话时间
    from datetime import datetime
    memory.setdefault("conversation_history", {})["last_interaction"] = datetime.now().isoformat()

    # 保存
    manager._save()

    # 同时添加到ChromaDB（如果有）
    manager.add_memory(f"{category}.{key} = {value}", memory_type="fact")

    return {
        "content": f"已更新: {category}.{key} = {value}",
        "is_error": False
    }


def search_memory(query: str) -> dict:
    """
    语义搜索用户记忆。
    用这个工具来查找与用户问题相关的历史记忆。
    """
    manager = get_memory_manager()
    results = manager.search_memory(query, n_results=5)

    if not results:
        return {
            "content": "未找到相关记忆",
            "is_error": False
        }

    formatted = "\n".join([f"- {r['content']} (相关度: {r['score']:.2f})" for r in results])
    return {
        "content": f"找到 {len(results)} 条相关记忆:\n{formatted}",
        "is_error": False
    }


# 工具定义
TOOL_DEFINITIONS = [
    {
        "name": "read_user_memory",
        "description": "读取用户的记忆，包括喜好、习惯、常问的问题。在回答前调用，让回答更个性化。",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "function": read_memory
    },
    {
        "name": "update_user_memory",
        "description": "当发现用户的新习惯、喜好、或重要信息时，保存到记忆中。比如用户说喜欢什么、讨厌什么、名字、常做什么。",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "记忆分类: preferences(喜好), habits(习惯), personal_notes(备注), user_name(名字), conversation_history(对话历史)",
                    "enum": ["preferences", "habits", "personal_notes", "user_name", "conversation_history"]
                },
                "key": {
                    "type": "string",
                    "description": "字段名，如 likes, dislikes, common_commands, active_hours, location, topics_discussed, tools_used"
                },
                "value": {
                    "type": "string",
                    "description": "要保存的值"
                }
            },
            "required": ["category", "key", "value"]
        },
        "function": update_memory
    },
    {
        "name": "search_user_memory",
        "description": "语义搜索用户记忆。当需要查找与用户问题相关的历史记忆时使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                }
            },
            "required": ["query"]
        },
        "function": search_memory
    }
]
