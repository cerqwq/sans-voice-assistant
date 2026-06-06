"""
文件Agent - 文件整理、内容搜索、格式转换
"""

import os
import shutil
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


class FileAgent:
    """文件Agent - 智能文件管理"""

    def __init__(self):
        self.scan_history = []

    def scan_directory(self, directory: str, recursive: bool = True) -> Dict[str, Any]:
        """扫描目录"""
        if not os.path.exists(directory):
            return {"error": f"目录不存在: {directory}"}

        result = {
            "directory": directory,
            "total_files": 0,
            "total_dirs": 0,
            "total_size": 0,
            "file_types": {},
            "largest_files": [],
            "scan_time": datetime.now().isoformat()
        }

        for root, dirs, files in os.walk(directory):
            result["total_dirs"] += len(dirs)
            result["total_files"] += len(files)

            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    result["total_size"] += size

                    # 统计文件类型
                    ext = os.path.splitext(file)[1].lower() or "无扩展名"
                    result["file_types"][ext] = result["file_types"].get(ext, 0) + 1

                    # 记录大文件
                    result["largest_files"].append({
                        "path": file_path,
                        "size": size,
                        "name": file
                    })

                except (PermissionError, OSError):
                    continue

            if not recursive:
                break

        # 排序大文件列表
        result["largest_files"].sort(key=lambda x: x["size"], reverse=True)
        result["largest_files"] = result["largest_files"][:10]

        # 格式化大小
        result["total_size_formatted"] = self._format_bytes(result["total_size"])

        self.scan_history.append(result)
        return result

    def find_duplicates(self, directory: str) -> List[List[str]]:
        """查找重复文件"""
        hash_map = {}

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # 计算文件哈希
                    file_hash = self._calculate_hash(file_path)
                    if file_hash:
                        if file_hash not in hash_map:
                            hash_map[file_hash] = []
                        hash_map[file_hash].append(file_path)
                except (PermissionError, OSError):
                    continue

        # 返回重复文件组
        duplicates = [paths for paths in hash_map.values() if len(paths) > 1]
        return duplicates

    def _calculate_hash(self, file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """计算文件哈希"""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def organize_by_type(self, directory: str, target_dir: str = None) -> Dict[str, Any]:
        """按文件类型整理"""
        if not os.path.exists(directory):
            return {"error": f"目录不存在: {directory}"}

        target_dir = target_dir or os.path.join(directory, "organized")
        os.makedirs(target_dir, exist_ok=True)

        moved = 0
        errors = 0

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # 获取文件类型
                    ext = os.path.splitext(file)[1].lower() or "other"
                    type_dir = os.path.join(target_dir, ext.lstrip('.'))
                    os.makedirs(type_dir, exist_ok=True)

                    # 移动文件
                    dest = os.path.join(type_dir, file)
                    if not os.path.exists(dest):
                        shutil.move(file_path, dest)
                        moved += 1
                except (PermissionError, OSError):
                    errors += 1

        return {
            "moved": moved,
            "errors": errors,
            "target": target_dir
        }

    def search_files(self, directory: str, pattern: str = "*", content: str = None) -> List[str]:
        """搜索文件"""
        results = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)

                # 名称匹配
                if pattern != "*" and pattern not in file:
                    continue

                # 内容匹配
                if content:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            if content not in f.read():
                                continue
                    except (PermissionError, OSError):
                        continue

                results.append(file_path)

        return results

    def get_directory_tree(self, directory: str, max_depth: int = 3) -> str:
        """获取目录树"""
        if not os.path.exists(directory):
            return f"目录不存在: {directory}"

        tree = []
        for root, dirs, files in os.walk(directory):
            depth = root.replace(directory, '').count(os.sep)
            if depth > max_depth:
                continue

            indent = '  ' * depth
            tree.append(f"{indent}{os.path.basename(root)}/")

            sub_indent = '  ' * (depth + 1)
            for file in files[:10]:  # 限制显示数量
                tree.append(f"{sub_indent}{file}")
            if len(files) > 10:
                tree.append(f"{sub_indent}... 还有 {len(files) - 10} 个文件")

        return '\n'.join(tree)

    def clean_empty_dirs(self, directory: str) -> int:
        """清理空目录"""
        removed = 0
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        removed += 1
                except (PermissionError, OSError):
                    continue

        return removed

    def _format_bytes(self, bytes: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024
        return f"{bytes:.1f}PB"


# 创建全局实例
file_agent = FileAgent()
