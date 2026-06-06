"""
工具函数单元测试
"""
import pytest
import os
import tempfile


def test_get_datetime_location():
    """测试获取时间日期位置"""
    from tools.datetime_location import get_datetime_location
    result = get_datetime_location()
    assert "当前时间" in result or "时间" in result


def test_weather_tool_definition():
    """测试天气工具定义"""
    from tools.weather import WEATHER_TOOL
    assert WEATHER_TOOL["name"] == "get_weather"
    assert "description" in WEATHER_TOOL
    assert "input_schema" in WEATHER_TOOL


def test_file_operations_read_file():
    """测试文件读取"""
    from tools.file_operations import read_file

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("测试内容")
        temp_path = f.name

    try:
        result = read_file(temp_path)
        assert "测试内容" in result
    finally:
        os.unlink(temp_path)


def test_file_operations_write_file():
    """测试文件写入"""
    from tools.file_operations import write_file

    temp_path = tempfile.mktemp(suffix='.txt')
    try:
        result = write_file(temp_path, "写入测试")
        assert "写入成功" in result
        assert os.path.exists(temp_path)

        # 验证内容
        with open(temp_path, 'r', encoding='utf-8') as f:
            assert f.read() == "写入测试"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_file_operations_list_directory():
    """测试目录列表"""
    from tools.file_operations import list_directory
    result = list_directory(".")
    assert isinstance(result, str)


def test_file_operations_execute_command_safe():
    """测试安全命令执行"""
    from tools.file_operations import execute_command
    result = execute_command("echo hello")
    assert "hello" in result


def test_file_operations_execute_command_dangerous():
    """测试危险命令拦截"""
    from tools.file_operations import execute_command
    result = execute_command("rm -rf /")
    assert "安全警告" in result


def test_file_operations_execute_python_safe():
    """测试安全Python执行"""
    from tools.file_operations import execute_python
    result = execute_python("print('hello')")
    assert "hello" in result


def test_file_operations_execute_python_dangerous():
    """测试危险Python拦截"""
    from tools.file_operations import execute_python
    result = execute_python("import os; os.system('rm -rf /')")
    assert "安全警告" in result
