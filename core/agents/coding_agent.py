"""
编码Agent - 代码生成、代码审查、重构优化
接入 LLM，真正执行代码相关任务
"""

import re
import ast
from typing import List, Dict, Any

from core.agents.base import BaseAgent, AgentResult


class CodingAgent(BaseAgent):
    """编码 Agent - 处理代码相关任务"""

    name = "coding"
    description = "代码生成、审查、重构、解释"
    capabilities = ["generate_code", "review_code", "refactor", "explain", "find_bugs"]

    # 任务关键词
    KEYWORDS = [
        "写代码", "代码", "编程", "函数", "类", "重构", "优化代码",
        "review", "审查", "debug", "找bug", "解释代码", "代码解释",
        "write code", "function", "class", "refactor",
    ]

    def can_handle(self, task: str) -> float:
        """评估置信度"""
        task_lower = task.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in task_lower)
        if matches == 0:
            return 0.0
        # 有代码块也加分
        if "```" in task:
            matches += 2
        return min(1.0, matches * 0.3)

    def run(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """执行编码任务"""
        context = context or {}

        # 判断任务子类型
        if any(kw in task for kw in ["审查", "review", "检查代码"]):
            result = self._review_task(task)
        elif any(kw in task for kw in ["重构", "refactor", "优化"]):
            result = self._refactor_task(task)
        elif any(kw in task for kw in ["解释", "explain", "这段代码"]):
            result = self._explain_task(task)
        elif any(kw in task for kw in ["bug", "错误", "问题"]):
            result = self._debug_task(task)
        else:
            result = self._generate_task(task)

        self._record(task, result)
        return AgentResult(
            agent_name=self.name,
            success=True,
            content=result,
        )

    def _generate_task(self, task: str) -> str:
        """生成代码"""
        system = (
            "你是 Sans 的编码助手。用户会描述需要什么代码，你直接生成代码。"
            "只输出代码，加简短注释，不要长篇解释。"
        )
        return self._call_llm(task, system=system, max_tokens=2048)

    def _review_task(self, task: str) -> str:
        """审查代码"""
        # 提取代码块
        code = self._extract_code(task)
        if not code:
            return "请提供要审查的代码"

        # 先做静态分析
        issues = self._static_analysis(code)

        # 再用 LLM 深度审查
        prompt = f"审查以下代码，指出问题和改进建议：\n\n```\n{code}\n```"
        system = "你是代码审查专家。简洁列出问题，用编号。"
        llm_review = self._call_llm(prompt, system=system)

        # 合并结果
        parts = []
        if issues:
            parts.append("**静态分析发现：**\n" + "\n".join(f"- {i}" for i in issues))
        if llm_review:
            parts.append(f"**深度审查：**\n{llm_review}")
        return "\n\n".join(parts) if parts else "代码没有明显问题"

    def _refactor_task(self, task: str) -> str:
        """重构代码"""
        code = self._extract_code(task)
        if not code:
            return "请提供要重构的代码"

        prompt = f"重构以下代码，提升可读性和质量：\n\n```\n{code}\n```\n\n直接输出重构后的代码。"
        system = "你是代码重构专家。直接输出改进后的代码，加简短注释说明改了什么。"
        return self._call_llm(prompt, system=system, max_tokens=2048)

    def _explain_task(self, task: str) -> str:
        """解释代码"""
        code = self._extract_code(task)
        if not code:
            return "请提供要解释的代码"

        prompt = f"解释以下代码的功能和逻辑：\n\n```\n{code}\n```"
        system = "简洁解释代码，不超过5句话。"
        return self._call_llm(prompt, system=system)

    def _debug_task(self, task: str) -> str:
        """调试代码"""
        code = self._extract_code(task)
        if not code:
            return "请提供有问题的代码和错误信息"

        prompt = f"找出以下代码的 bug 并修复：\n\n```\n{code}\n```"
        system = "你是调试专家。指出 bug 位置，给出修复后的代码。"
        return self._call_llm(prompt, system=system, max_tokens=2048)

    def _extract_code(self, text: str) -> str:
        """从文本中提取代码块"""
        # 尝试提取 ``` 包裹的代码
        match = re.search(r'```(?:\w*\n)?(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 如果没有代码块，检查是否有明显的代码特征
        lines = text.strip().split('\n')
        code_lines = [l for l in lines if any(kw in l for kw in ['def ', 'class ', 'import ', 'for ', 'if ', 'return ', 'print('])]
        if len(code_lines) >= 2:
            return '\n'.join(code_lines)

        return ""

    def _static_analysis(self, code: str) -> List[str]:
        """静态分析（不依赖 LLM）"""
        issues = []

        # 语法检查
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"语法错误 (行 {e.lineno}): {e.msg}")

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"行 {i}: 超过120字符")
            if re.search(r'except\s*:', line):
                issues.append(f"行 {i}: 裸 except，应指定异常类型")
            if re.search(r'(api_key|password|secret)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                issues.append(f"行 {i}: 可能的硬编码密钥")

        return issues


# 全局实例
coding_agent = CodingAgent()
