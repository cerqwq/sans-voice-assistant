"""
BaseAgent - 所有专门 Agent 的抽象基类
定义统一接口：能力声明、任务处理、置信度评估
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentMessage:
    """Agent 间通信消息"""
    sender: str
    receiver: str
    task: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentResult:
    """Agent 执行结果"""
    agent_name: str
    success: bool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent(ABC):
    """所有专门 Agent 的基类"""

    name: str = "base"
    description: str = "基础 Agent"
    capabilities: List[str] = []

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.history: List[Dict[str, Any]] = []

    @abstractmethod
    def can_handle(self, task: str) -> float:
        """
        评估该 Agent 处理此任务的置信度
        Returns: 0.0 ~ 1.0
        """
        ...

    @abstractmethod
    def run(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        执行任务
        Args:
            task: 任务描述
            context: 上下文信息（其他 Agent 的结果、用户历史等）
        Returns:
            AgentResult
        """
        ...

    def _call_llm(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        """调用 LLM（如果可用）"""
        if not self.llm:
            return f"[{self.name}] LLM 未配置，无法执行"

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self.llm.chat.completions.create(
                model=self.llm._model if hasattr(self.llm, '_model') else "qwen3.5:2b",
                max_tokens=max_tokens,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[{self.name}] LLM 调用失败: {e}"

    def _record(self, task: str, result: str):
        """记录执行历史"""
        self.history.append({
            "task": task,
            "result": result[:500],
            "timestamp": datetime.now().isoformat(),
        })
        # 只保留最近 20 条
        if len(self.history) > 20:
            self.history = self.history[-20:]
