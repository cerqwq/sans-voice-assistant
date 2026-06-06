"""
Sans Agent 模块
包含6个专门Agent：自动化、研究、编码、监控、学习、文件
"""

from .base import BaseAgent, AgentResult, AgentMessage
from .automation_agent import AutomationAgent, automation_agent
from .research_agent import ResearchAgent, research_agent
from .coding_agent import CodingAgent, coding_agent
from .monitor_agent import MonitorAgent, monitor_agent
from .learning_agent import LearningAgent, learning_agent
from .file_agent import FileAgent, file_agent

__all__ = [
    'BaseAgent', 'AgentResult', 'AgentMessage',
    'AutomationAgent', 'automation_agent',
    'ResearchAgent', 'research_agent',
    'CodingAgent', 'coding_agent',
    'MonitorAgent', 'monitor_agent',
    'LearningAgent', 'learning_agent',
    'FileAgent', 'file_agent',
]
