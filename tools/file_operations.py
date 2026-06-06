"""
文件操作工具 - Agent的核心工具
支持读取、写入、搜索、执行代码等操作
"""

import os
import re
import subprocess
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(path: str, encoding: str = "utf-8") -> str:
    """读取文件内容"""
    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
        return f"文件内容 ({len(content)} 字符):\n{content[:5000]}"
    except Exception as e:
        return f"读取失败: {e}"


def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """写入文件内容"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        return f"写入成功: {path}"
    except Exception as e:
        return f"写入失败: {e}"


def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """列出目录内容"""
    try:
        items = []
        for item in os.listdir(path):
            if not show_hidden and item.startswith('.'):
                continue
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                items.append(f"📁 {item}/")
            else:
                size = os.path.getsize(full_path)
                items.append(f"📄 {item} ({size} bytes)")
        return "\n".join(items[:50])  # 限制输出
    except Exception as e:
        return f"列出目录失败: {e}"


def search_files(pattern: str, path: str = ".") -> str:
    """搜索文件"""
    import glob
    try:
        matches = glob.glob(os.path.join(path, pattern), recursive=True)
        if not matches:
            return f"未找到匹配 '{pattern}' 的文件"
        return f"找到 {len(matches)} 个文件:\n" + "\n".join(matches[:20])
    except Exception as e:
        return f"搜索失败: {e}"


# 危险命令列表（使用正则匹配，防止绕过）
DANGEROUS_COMMANDS = [
    r'rm\s+-rf', r'rmdir\s+/s', r'del\s+/f', r'format\b', r'fdisk\b',
    r'shutdown\b', r'restart\b', r'taskkill\b', r'net\s+user', r'net\s+localgroup',
    r'reg\s+delete', r'reg\s+add', r'powershell\b', r'pwsh\b', r'cmd\b',
    r'chmod\b', r'chown\b', r'mkfs\b', r'dd\s+if=',
    r'curl\b.*\|\s*(bash|sh)', r'wget\b.*\|\s*(bash|sh)',
    r'>\s*/dev/', r'mkfifo\b', r'nc\s+-l',
]


def execute_command(command: str, timeout: int = 30, confirm: bool = False) -> str:
    """执行系统命令（带安全检查）"""
    # 安全检查 - 使用正则匹配，防止空格绕过
    command_stripped = command.strip()
    for pattern in DANGEROUS_COMMANDS:
        if re.search(pattern, command_stripped, re.IGNORECASE):
            logger.warning(f"危险命令被拦截: {command_stripped[:100]}")
            return f"[安全警告] 检测到危险命令模式 '{pattern}'。如需执行，请使用 confirm=True 参数。"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8'
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return f"命令执行完成 (返回码: {result.returncode}):\n{output[:2000]}"
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"命令执行失败: {e}"


# 危险Python代码模式（正则匹配）
DANGEROUS_PYTHON = [
    r'os\.system\s*\(', r'subprocess\.', r'eval\s*\(', r'exec\s*\(',
    r'__import__\s*\(', r'shutil\.rmtree\s*\(', r'os\.remove\s*\(',
    r'os\.unlink\s*\(', r'os\.rmdir\s*\(', r'sys\.exit\s*\(',
    r'ctypes\.', r'signal\.', r'gc\.collect',
]


def execute_python(code: str, confirm: bool = False) -> str:
    """执行Python代码（带安全检查）"""
    # 安全检查 - 使用正则匹配
    for pattern in DANGEROUS_PYTHON:
        if re.search(pattern, code, re.IGNORECASE):
            logger.warning(f"危险Python代码被拦截: {pattern}")
            return f"[安全警告] 检测到危险代码模式 '{pattern}'。如需执行，请使用 confirm=True 参数。"

    try:
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name

        # 执行代码
        result = subprocess.run(
            ['python', temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8'
        )

        # 清理临时文件
        os.unlink(temp_path)

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return f"Python执行完成:\n{output[:2000]}"
    except subprocess.TimeoutExpired:
        return "Python执行超时"
    except Exception as e:
        return f"Python执行失败: {e}"


def get_file_info(path: str) -> str:
    """获取文件信息"""
    try:
        stat = os.stat(path)
        return json.dumps({
            "path": path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_file": os.path.isfile(path),
            "is_dir": os.path.isdir(path),
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"获取文件信息失败: {e}"


# 工具定义
READ_FILE_TOOL = {
    "name": "read_file",
    "description": "读取文件内容。可以读取文本文件、代码文件等。",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "encoding": {"type": "string", "description": "文件编码，默认utf-8"}
        },
        "required": ["path"]
    }
}

WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": "写入文件内容。可以创建新文件或覆盖现有文件。",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"},
            "encoding": {"type": "string", "description": "文件编码，默认utf-8"}
        },
        "required": ["path", "content"]
    }
}

LIST_DIRECTORY_TOOL = {
    "name": "list_directory",
    "description": "列出目录中的文件和子目录。",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径，默认当前目录"},
            "show_hidden": {"type": "boolean", "description": "是否显示隐藏文件"}
        }
    }
}

SEARCH_FILES_TOOL = {
    "name": "search_files",
    "description": "搜索匹配指定模式的文件。",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "搜索模式，如 '*.py' 或 '**/*.txt'"},
            "path": {"type": "string", "description": "搜索路径，默认当前目录"}
        },
        "required": ["pattern"]
    }
}

EXECUTE_COMMAND_TOOL = {
    "name": "execute_command",
    "description": "执行系统命令。可以运行任何shell命令。",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的命令"},
            "timeout": {"type": "integer", "description": "超时时间（秒），默认30"}
        },
        "required": ["command"]
    }
}

EXECUTE_PYTHON_TOOL = {
    "name": "execute_python",
    "description": "执行Python代码。可以运行任意Python脚本。",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的Python代码"}
        },
        "required": ["code"]
    }
}

GET_FILE_INFO_TOOL = {
    "name": "get_file_info",
    "description": "获取文件的详细信息，包括大小、修改时间等。",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"}
        },
        "required": ["path"]
    }
}
