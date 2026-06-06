"""
工具注册表单元测试
"""
import pytest


def test_tool_registry_init():
    """测试ToolRegistry初始化"""
    from core.tool_registry import ToolRegistry
    registry = ToolRegistry()
    assert len(registry._tools) == 0
    assert len(registry._handlers) == 0


def test_tool_registry_register():
    """测试工具注册"""
    from core.tool_registry import ToolRegistry
    registry = ToolRegistry()

    # 定义测试工具
    def test_handler(param: str) -> str:
        return f"结果: {param}"

    tool_def = {
        "name": "test_tool",
        "description": "测试工具",
        "input_schema": {
            "type": "object",
            "properties": {
                "param": {"type": "string"}
            }
        }
    }

    # 注册工具
    registry.register(tool_def, test_handler)

    assert "test_tool" in registry._tools
    assert "test_tool" in registry._handlers


def test_tool_registry_execute():
    """测试工具执行"""
    from core.tool_registry import ToolRegistry
    registry = ToolRegistry()

    # 定义测试工具
    def test_handler(param: str) -> str:
        return f"结果: {param}"

    tool_def = {
        "name": "test_tool",
        "description": "测试工具",
        "input_schema": {}
    }

    registry.register(tool_def, test_handler)

    # 执行工具
    result = registry.execute("test_tool", {"param": "测试"})
    assert result["content"] == "结果: 测试"
    assert "is_error" not in result


def test_tool_registry_execute_unknown():
    """测试执行未知工具"""
    from core.tool_registry import ToolRegistry
    registry = ToolRegistry()

    result = registry.execute("unknown_tool", {})
    assert result["is_error"] is True
    assert "Unknown tool" in result["content"]


def test_create_default_registry():
    """测试创建默认注册表"""
    from core.tool_registry import create_default_registry
    registry = create_default_registry()

    # 检查是否注册了工具
    tools = registry.get_tool_definitions()
    assert len(tools) > 0

    # 检查工具名称
    tool_names = [t["name"] for t in tools]
    assert "get_datetime_location" in tool_names
    assert "get_weather" in tool_names
