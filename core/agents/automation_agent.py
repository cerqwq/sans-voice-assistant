"""
自动化Agent - 定时任务、自动备份、自动清理
"""

import os
import shutil
import schedule
import time
import threading
from datetime import datetime
from pathlib import Path


class AutomationAgent:
    """自动化Agent - 处理定时任务和自动化操作"""

    name = "automation"
    description = "定时任务、自动备份、自动清理"
    capabilities = ["cleanup", "backup", "disk_check", "process_monitor"]

    KEYWORDS = ["定时", "自动", "备份", "清理", "计划任务", "每天", "每周", "每小时", "磁盘空间"]

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in task_lower)
        return min(1.0, matches * 0.4) if matches else 0.0

    def __init__(self):
        self.tasks = {}
        self.running = False
        self.thread = None

    def add_task(self, name: str, func, schedule_time: str, *args, **kwargs):
        """
        添加定时任务

        Args:
            name: 任务名称
            func: 任务函数
            schedule_time: 时间表达式，如 "每天 08:00", "每小时", "每周一"
            *args, **kwargs: 传递给任务函数的参数
        """
        self.tasks[name] = {
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "schedule": schedule_time,
            "last_run": None,
            "status": "pending"
        }

    def remove_task(self, name: str):
        """移除任务"""
        if name in self.tasks:
            del self.tasks[name]

    def list_tasks(self) -> list:
        """列出所有任务"""
        return [
            {
                "name": name,
                "schedule": task["schedule"],
                "status": task["status"],
                "last_run": task["last_run"]
            }
            for name, task in self.tasks.items()
        ]

    def run_task(self, name: str) -> str:
        """手动执行任务"""
        if name not in self.tasks:
            return f"任务 {name} 不存在"

        task = self.tasks[name]
        try:
            result = task["func"](*task["args"], **task["kwargs"])
            task["last_run"] = datetime.now().isoformat()
            task["status"] = "success"
            return f"任务 {name} 执行成功: {result}"
        except Exception as e:
            task["status"] = "failed"
            return f"任务 {name} 执行失败: {e}"

    def start(self):
        """启动定时任务调度器"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _run_scheduler(self):
        """运行调度器"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def run(self, task: str, context: dict = None):
        """执行自动化任务（兼容 Orchestrator 接口）"""
        from core.agents.base import AgentResult
        task_lower = task.lower()

        if "清理" in task_lower:
            result = cleanup_temp_files()
        elif "备份" in task_lower:
            result = "请指定备份源目录和目标目录"
        elif "磁盘" in task_lower or "空间" in task_lower:
            result = check_disk_space()
        else:
            tasks = self.list_tasks()
            task_list = "\n".join(f"  - {t['name']} ({t['schedule']})" for t in tasks)
            result = f"可用的自动化任务:\n{task_list}"

        return AgentResult(agent_name=self.name, success=True, content=result)


# 预定义的自动化任务

def cleanup_temp_files():
    """清理临时文件"""
    temp_dirs = [
        os.environ.get('TEMP', ''),
        os.environ.get('TMP', ''),
        os.path.expanduser('~/AppData/Local/Temp')
    ]

    cleaned = 0
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        # 删除超过7天的文件
                        if time.time() - os.path.getmtime(item_path) > 7 * 24 * 3600:
                            os.remove(item_path)
                            cleaned += 1
                except (PermissionError, OSError):
                    pass

    return f"清理了 {cleaned} 个临时文件"


def backup_important_files(source_dir: str, backup_dir: str):
    """备份重要文件"""
    if not os.path.exists(source_dir):
        return f"源目录不存在: {source_dir}"

    # 创建备份目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)

    # 复制文件
    copied = 0
    for item in os.listdir(source_dir):
        source = os.path.join(source_dir, item)
        dest = os.path.join(backup_path, item)
        try:
            if os.path.isfile(source):
                shutil.copy2(source, dest)
                copied += 1
        except (PermissionError, OSError):
            pass

    return f"备份了 {copied} 个文件到 {backup_path}"


def check_disk_space():
    """检查磁盘空间"""
    results = []
    for drive in ['C:', 'D:', 'E:']:
        if os.path.exists(drive):
            total, used, free = shutil.disk_usage(drive)
            free_gb = free / (1024 ** 3)
            results.append(f"{drive}: {free_gb:.1f}GB 可用")

    return "\n".join(results)


def monitor_process(process_name: str):
    """监控进程状态"""
    import psutil

    for proc in psutil.process_iter(['name', 'status']):
        if proc.info['name'] == process_name:
            return f"{process_name}: {proc.info['status']}"

    return f"{process_name}: 未运行"


# 创建全局实例
automation_agent = AutomationAgent()

# 添加默认任务
automation_agent.add_task("清理临时文件", cleanup_temp_files, "每天 02:00")
automation_agent.add_task("检查磁盘空间", check_disk_space, "每天 08:00")
