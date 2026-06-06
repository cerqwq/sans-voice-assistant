"""
记忆管理器单元测试
"""
import pytest
import json
import tempfile
from pathlib import Path


def test_memory_manager_init():
    """测试MemoryManager初始化"""
    from core.memory_manager import MemoryManager
    manager = MemoryManager()
    assert manager.memory is not None
    assert isinstance(manager.memory, dict)


def test_memory_manager_load_save():
    """测试记忆加载和保存"""
    from core.memory_manager import MemoryManager
    manager = MemoryManager()

    # 修改记忆
    manager.memory["user_name"] = "测试用户"
    manager._save()

    # 重新加载
    manager2 = MemoryManager()
    assert manager2.memory.get("user_name") == "测试用户"

    # 清理
    manager.memory["user_name"] = ""
    manager._save()


def test_memory_manager_add_memory():
    """测试添加记忆"""
    from core.memory_manager import MemoryManager
    manager = MemoryManager()

    # 添加事实
    manager.add_memory("测试事实", memory_type="fact")
    assert any("测试事实" in str(f) for f in manager.memory.get("facts", []))

    # 添加备注
    manager.add_memory("测试备注", memory_type="note")
    assert "测试备注" in manager.memory.get("personal_notes", [])


def test_memory_manager_update_from_conversation():
    """测试从对话中提取信息"""
    from core.memory_manager import MemoryManager
    manager = MemoryManager()

    # 检测名字
    manager.update_from_conversation("我叫张三", "你好张三")
    assert manager.memory.get("user_name") == "张三"

    # 检测喜好
    manager.update_from_conversation("我喜欢编程", "编程很棒")
    assert "编程" in manager.memory.get("preferences", {}).get("likes", [])


def test_memory_manager_get_system_prompt():
    """测试获取系统提示"""
    from core.memory_manager import MemoryManager
    manager = MemoryManager()

    # 设置记忆
    manager.memory["user_name"] = "测试用户"
    manager.memory["preferences"]["likes"] = ["音乐"]

    # 获取提示
    prompt = manager.get_system_prompt_with_memory("基础提示")
    assert "测试用户" in prompt
    assert "音乐" in prompt
