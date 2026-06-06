"""
唤醒词检测单元测试
"""
import pytest


def test_contains_wake_word():
    """测试唤醒词检测"""
    from main import contains_wake_word

    # 正确的唤醒词
    assert contains_wake_word("hi sans") is True
    assert contains_wake_word("Hi Sans") is True
    assert contains_wake_word("嘿三思") is True
    assert contains_wake_word("嗨 sans") is True

    # 错误的输入
    assert contains_wake_word("你好") is False
    assert contains_wake_word("hello") is False
    assert contains_wake_word("") is False
    assert contains_wake_word(None) is False


def test_extract_command():
    """测试命令提取"""
    from main import extract_command

    # 唤醒词 + 命令
    assert extract_command("hi sans 今天天气怎么样") == "今天天气怎么样"
    assert extract_command("Hi Sans, 打开浏览器") == "打开浏览器"

    # 只有唤醒词
    assert extract_command("hi sans") == ""
    assert extract_command("嘿三思") == ""

    # 空输入
    assert extract_command("") == ""
    assert extract_command(None) == ""
