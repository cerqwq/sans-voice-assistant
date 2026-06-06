"""
监控Agent - 系统监控、进程监控、网络监控
"""

import os
import time
import psutil
import socket
from typing import Dict, Any, List
from datetime import datetime


class MonitorAgent:
    """监控Agent - 实时监控系统状态"""

    name = "monitor"
    description = "系统监控、进程监控、网络监控"
    capabilities = ["cpu", "memory", "disk", "network", "process"]

    KEYWORDS = ["监控", "系统状态", "cpu", "内存", "磁盘", "进程", "网络状态", "系统信息"]

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in task_lower)
        return min(1.0, matches * 0.4) if matches else 0.0

    def __init__(self):
        self.alerts = []
        self.thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90
        }

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统整体状态"""
        return {
            "cpu": self.get_cpu_status(),
            "memory": self.get_memory_status(),
            "disk": self.get_disk_status(),
            "network": self.get_network_status(),
            "timestamp": datetime.now().isoformat()
        }

    def get_cpu_status(self) -> Dict[str, Any]:
        """获取CPU状态"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        return {
            "percent": cpu_percent,
            "count": cpu_count,
            "freq_current": cpu_freq.current if cpu_freq else None,
            "freq_max": cpu_freq.max if cpu_freq else None,
            "status": "warning" if cpu_percent > self.thresholds["cpu_percent"] else "normal"
        }

    def get_memory_status(self) -> Dict[str, Any]:
        """获取内存状态"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total": self._format_bytes(memory.total),
            "available": self._format_bytes(memory.available),
            "used": self._format_bytes(memory.used),
            "percent": memory.percent,
            "swap_total": self._format_bytes(swap.total),
            "swap_percent": swap.percent,
            "status": "warning" if memory.percent > self.thresholds["memory_percent"] else "normal"
        }

    def get_disk_status(self) -> Dict[str, Any]:
        """获取磁盘状态"""
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total": self._format_bytes(usage.total),
                    "used": self._format_bytes(usage.used),
                    "free": self._format_bytes(usage.free),
                    "percent": usage.percent,
                    "status": "warning" if usage.percent > self.thresholds["disk_percent"] else "normal"
                })
            except PermissionError:
                continue

        return {"disks": disks}

    def get_network_status(self) -> Dict[str, Any]:
        """获取网络状态"""
        net_io = psutil.net_io_counters()
        connections = psutil.net_connections(kind='inet')

        return {
            "bytes_sent": self._format_bytes(net_io.bytes_sent),
            "bytes_recv": self._format_bytes(net_io.bytes_recv),
            "connections": len(connections),
            "is_connected": self._check_internet()
        }

    def _check_internet(self) -> bool:
        """检查网络连接"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def get_process_list(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取进程列表"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 按CPU使用率排序
        processes.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
        return processes[:top_n]

    def monitor_process(self, process_name: str) -> Dict[str, Any]:
        """监控特定进程"""
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['name'] == process_name:
                    return {
                        "found": True,
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "status": proc.info['status'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent']
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {"found": False, "name": process_name}

    def check_alerts(self) -> List[Dict[str, Any]]:
        """检查告警"""
        alerts = []

        # CPU告警
        cpu = self.get_cpu_status()
        if cpu["status"] == "warning":
            alerts.append({
                "type": "cpu",
                "level": "warning",
                "message": f"CPU使用率过高: {cpu['percent']}%"
            })

        # 内存告警
        memory = self.get_memory_status()
        if memory["status"] == "warning":
            alerts.append({
                "type": "memory",
                "level": "warning",
                "message": f"内存使用率过高: {memory['percent']}%"
            })

        # 磁盘告警
        disk = self.get_disk_status()
        for d in disk["disks"]:
            if d["status"] == "warning":
                alerts.append({
                    "type": "disk",
                    "level": "warning",
                    "message": f"磁盘 {d['device']} 使用率过高: {d['percent']}%"
                })

        return alerts

    def _format_bytes(self, bytes: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024
        return f"{bytes:.1f}PB"

    def run(self, task: str, context: dict = None):
        """执行监控任务（兼容 Orchestrator 接口）"""
        from core.agents.base import AgentResult
        task_lower = task.lower()

        if "cpu" in task_lower:
            status = self.get_cpu_status()
            content = f"CPU使用率: {status['percent']}%, 核心数: {status['count']}"
        elif "内存" in task_lower:
            status = self.get_memory_status()
            content = f"内存使用率: {status['percent']}%, 可用: {status['available']}"
        elif "磁盘" in task_lower:
            status = self.get_disk_status()
            disks = [f"{d['device']}: {d['percent']}%" for d in status['disks']]
            content = f"磁盘状态: {', '.join(disks)}"
        elif "网络" in task_lower:
            status = self.get_network_status()
            content = f"网络连接: {'正常' if status['is_connected'] else '断开'}, 连接数: {status['connections']}"
        elif "进程" in task_lower:
            processes = self.get_process_list(5)
            proc_list = [f"{p['name']}: {p['cpu_percent']}%" for p in processes]
            content = f"Top5进程: {', '.join(proc_list)}"
        else:
            status = self.get_system_status()
            content = f"系统状态 - CPU: {status['cpu']['percent']}%, 内存: {status['memory']['percent']}%"

        return AgentResult(agent_name=self.name, success=True, content=content)


# 创建全局实例
monitor_agent = MonitorAgent()
