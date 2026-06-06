"""
研究Agent - 信息收集、对比分析、概念解释
接入 LLM，真正执行研究任务
"""

from typing import List, Dict, Any

from core.agents.base import BaseAgent, AgentResult


class ResearchAgent(BaseAgent):
    """研究 Agent - 处理信息收集和分析任务"""

    name = "research"
    description = "信息研究、对比分析、概念解释、总结"
    capabilities = ["research", "compare", "explain", "summarize", "analyze"]

    KEYWORDS = [
        "研究", "分析", "对比", "比较", "总结", "解释", "什么是",
        "介绍", "调查", "区别", "优缺点", "哪个好",
        "research", "analyze", "compare", "summarize", "explain",
    ]

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in task_lower)
        if matches == 0:
            return 0.0
        return min(1.0, matches * 0.3)

    def run(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        context = context or {}

        if any(kw in task for kw in ["对比", "比较", "哪个好", "区别", "vs"]):
            result = self._compare_task(task)
        elif any(kw in task for kw in ["总结", "摘要", "概括"]):
            result = self._summarize_task(task)
        elif any(kw in task for kw in ["什么是", "解释", "介绍", "是什么"]):
            result = self._explain_task(task)
        else:
            result = self._research_task(task)

        self._record(task, result)
        return AgentResult(
            agent_name=self.name,
            success=True,
            content=result,
        )

    def _research_task(self, task: str) -> str:
        """通用研究任务"""
        system = (
            "你是 Sans 的研究助手。用户会提出研究问题，你需要：\n"
            "1. 分析问题的核心\n"
            "2. 给出结构化的回答\n"
            "3. 如果有多个角度，分别列出\n"
            "简洁明了，不要废话。"
        )
        return self._call_llm(task, system=system)

    def _compare_task(self, task: str) -> str:
        """对比分析"""
        system = (
            "你是对比分析专家。用户会给出要对比的选项，你需要：\n"
            "1. 列出对比维度\n"
            "2. 每个维度逐项对比\n"
            "3. 给出推荐建议\n"
            "用表格或列表格式，清晰易读。"
        )
        return self._call_llm(task, system=system)

    def _summarize_task(self, task: str) -> str:
        """总结任务"""
        system = "你是总结专家。将用户提供的内容压缩为关键要点，不超过5点。"
        return self._call_llm(task, system=system)

    def _explain_task(self, task: str) -> str:
        """概念解释"""
        system = (
            "你是概念解释专家。用简洁的语言解释用户问的概念，包含：\n"
            "1. 一句话定义\n"
            "2. 核心原理（2-3句）\n"
            "3. 实际应用场景\n"
            "简洁自然，像跟朋友聊天一样。"
        )
        return self._call_llm(task, system=system)


# 全局实例
research_agent = ResearchAgent()
