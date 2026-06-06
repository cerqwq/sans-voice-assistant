"""
AutonomousAgent - 全自主智能体
自己提问、自己思考、自己进化、自己调用工具、自己解决问题
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SelfReflection:
    """自我反思模块 - 评估自身能力，发现知识缺口"""

    def __init__(self, llm_client, model: str = "qwen3.5:2b"):
        self.llm = llm_client
        self.model = model
        self.knowledge_gaps: List[str] = []
        self.success_history: List[Dict] = []
        self.failure_history: List[Dict] = []

    def reflect_on_task(self, task: str, result: str, success: bool) -> Dict[str, Any]:
        """反思任务执行"""
        if success:
            self.success_history.append({
                "task": task[:200],
                "result_summary": result[:200],
                "timestamp": datetime.now().isoformat(),
            })
        else:
            self.failure_history.append({
                "task": task[:200],
                "error": result[:200],
                "timestamp": datetime.now().isoformat(),
            })

        # 分析失败原因，生成改进建议
        if not success and self.llm:
            prompt = f"""分析这个任务为什么失败，给出改进建议：

任务: {task[:300]}
结果: {result[:300]}

返回JSON:
{{"reason": "失败原因", "improvement": "改进建议", "should_learn": true/false}}"""

            try:
                response = self.llm.chat.completions.create(
                    model=self.model,
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.choices[0].message.content or "{}"
                # 提取JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass

        return {"reason": "", "improvement": "", "should_learn": False}

    def identify_knowledge_gap(self, task: str) -> Optional[str]:
        """识别知识缺口"""
        # 检查是否有类似失败任务
        for failure in self.failure_history[-10:]:
            if self._similarity(task, failure["task"]) > 0.7:
                return f"之前处理类似任务失败: {failure['error'][:100]}"
        return None

    def _similarity(self, a: str, b: str) -> float:
        """简单相似度计算"""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def get_stats(self) -> Dict[str, Any]:
        """获取反思统计"""
        total = len(self.success_history) + len(self.failure_history)
        return {
            "total_tasks": total,
            "success_count": len(self.success_history),
            "failure_count": len(self.failure_history),
            "success_rate": f"{len(self.success_history)/total*100:.0f}%" if total else "N/A",
        }


class SelfEvolver:
    """自我进化模块 - 根据经验改进自身"""

    def __init__(self, memory_path: str = None):
        self.memory_path = memory_path or str(
            Path(__file__).parent.parent / "memory" / "agent_evolution.json"
        )
        self.strategies: Dict[str, Any] = self._load_strategies()
        self.prompt_improvements: List[str] = []

    def _load_strategies(self) -> Dict[str, Any]:
        """加载已学到的策略"""
        try:
            if Path(self.memory_path).exists():
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "task_approaches": {},
            "tool_preferences": {},
            "learned_patterns": [],
        }

    def _save_strategies(self):
        """保存策略"""
        try:
            Path(self.memory_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.strategies, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存策略失败: {e}")

    def record_approach(self, task_type: str, approach: str, success: bool):
        """记录任务处理方式"""
        if task_type not in self.strategies["task_approaches"]:
            self.strategies["task_approaches"][task_type] = []

        self.strategies["task_approaches"][task_type].append({
            "approach": approach,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })

        # 只保留最近 20 条
        self.strategies["task_approaches"][task_type] = \
            self.strategies["task_approaches"][task_type][-20:]

        self._save_strategies()

    def get_best_approach(self, task_type: str) -> Optional[str]:
        """获取最佳处理方式"""
        approaches = self.strategies["task_approaches"].get(task_type, [])
        if not approaches:
            return None

        # 统计成功率
        success_count = {}
        total_count = {}
        for a in approaches:
            approach = a["approach"]
            total_count[approach] = total_count.get(approach, 0) + 1
            if a["success"]:
                success_count[approach] = success_count.get(approach, 0) + 1

        # 返回成功率最高的
        best = max(total_count.keys(),
                   key=lambda x: success_count.get(x, 0) / total_count[x])
        return best

    def record_tool_preference(self, task_type: str, tool: str, effectiveness: float):
        """记录工具偏好"""
        if task_type not in self.strategies["tool_preferences"]:
            self.strategies["tool_preferences"][task_type] = {}

        self.strategies["tool_preferences"][task_type][tool] = \
            self.strategies["tool_preferences"][task_type].get(tool, 0) * 0.8 + effectiveness * 0.2

        self._save_strategies()

    def learn_pattern(self, pattern: str):
        """学习新模式"""
        if pattern not in self.strategies["learned_patterns"]:
            self.strategies["learned_patterns"].append(pattern)
            # 只保留最近 50 个
            self.strategies["learned_patterns"] = \
                self.strategies["learned_patterns"][-50:]
            self._save_strategies()


class AutonomousAgent:
    """
    全自主智能体
    - 自己提问：识别知识缺口，主动学习
    - 自己思考：多步推理，规划执行
    - 自己进化：根据经验改进策略
    - 自己调用工具：自主选择和使用工具
    - 自己解决问题：分解复杂任务，逐步解决
    """

    def __init__(self, assistant=None, orchestrator=None):
        # 延迟导入避免循环
        if assistant is None:
            from core.assistant import VoiceAssistant
            assistant = VoiceAssistant()
        self.assistant = assistant
        self.orchestrator = orchestrator

        # 核心模块
        self.reflection = SelfReflection(assistant.ollama_client, assistant.ollama_model)
        self.evolver = SelfEvolver()

        # 状态
        self.current_plan: List[Dict] = []
        self.execution_context: Dict[str, Any] = {}
        self.max_iterations = 15
        self.max_retries = 3

    def think(self, task: str) -> Dict[str, Any]:
        """思考：分析任务，制定计划"""
        # 1. 检查是否有已知策略
        task_type = self._classify_task(task)
        known_approach = self.evolver.get_best_approach(task_type)

        # 2. 检查是否有知识缺口
        gap = self.reflection.identify_knowledge_gap(task)

        # 3. 生成计划
        prompt = f"""你是一个自主智能体，需要分析任务并制定执行计划。

任务: {task}

{f"已知最佳策略: {known_approach}" if known_approach else ""}
{f"注意: {gap}" if gap else ""}

制定执行计划，返回JSON格式:
{{"steps": [{{"action": "具体操作", "tool": "需要的工具", "reason": "为什么这样做"}}], "complexity": "low/medium/high", "estimated_time": "分钟数"}}"""

        response = self.assistant.chat(prompt)

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                self.current_plan = plan.get("steps", [])
                return plan
        except Exception:
            pass

        # 回退：简单计划
        return {"steps": [{"action": task, "tool": "chat", "reason": "直接执行"}], "complexity": "low"}

    def act(self, step: Dict[str, Any]) -> str:
        """行动：执行单个步骤"""
        action = step.get("action", "")
        tool = step.get("tool", "chat")

        if tool == "chat":
            return self.assistant.chat(action)
        elif self.orchestrator:
            # 通过编排器执行
            result = self.orchestrator.execute(action, self.execution_context)
            return result.content if result.content else self.assistant.chat(action)
        else:
            return self.assistant.chat(action)

    def observe(self, action: str, result: str) -> Dict[str, Any]:
        """观察：分析执行结果"""
        success = len(result) > 10 and "错误" not in result[:50] and "失败" not in result[:50]

        return {
            "success": success,
            "result_length": len(result),
            "has_content": len(result) > 50,
        }

    def evolve(self, task: str, approach: str, success: bool):
        """进化：从经验中学习"""
        task_type = self._classify_task(task)
        self.evolver.record_approach(task_type, approach, success)
        self.reflection.reflect_on_task(task, approach, success)

    def solve(self, task: str) -> Generator[str, None, None]:
        """
        自主解决问题
        流程: 思考 → 行动 → 观察 → 反思 → 进化 → 循环
        """
        yield f"[自主Agent] 分析任务: {task}\n"

        # 思考
        plan = self.think(task)
        steps = plan.get("steps", [])
        complexity = plan.get("complexity", "low")

        yield f"[自主Agent] 计划: {len(steps)}步, 复杂度={complexity}\n"

        if not steps:
            yield "[自主Agent] 无法制定计划，直接执行\n"
            result = self.assistant.chat(task)
            yield result
            return

        # 执行循环
        context = f"任务: {task}\n"
        total_success = True

        for i, step in enumerate(steps[:self.max_iterations]):
            action = step.get("action", "")
            yield f"\n[Step {i+1}/{len(steps)}] {action}\n"

            # 行动
            result = self.act(step)

            # 观察
            observation = self.observe(action, result)

            if observation["success"]:
                yield f"  ✓ 成功 ({observation['result_length']}字符)\n"
                context += f"步骤{i+1}: 成功 - {result[:100]}\n"
            else:
                yield f"  ✗ 失败\n"
                total_success = False
                context += f"步骤{i+1}: 失败 - {result[:100]}\n"

                # 自我提问：为什么失败？
                yield "[自主Agent] 反思失败原因...\n"
                reflection = self.reflection.reflect_on_task(action, result, False)
                if reflection.get("improvement"):
                    yield f"  改进: {reflection['improvement']}\n"

                    # 重试 with 改进
                    improved_step = {**step, "action": f"{action}\n改进: {reflection['improvement']}"}
                    result = self.act(improved_step)
                    observation = self.observe(action, result)
                    if observation["success"]:
                        yield f"  ✓ 重试成功\n"

            # 展示结果
            yield f"  {result[:200]}\n"

        # 进化
        self.evolve(task, context[:500], total_success)

        # 总结
        stats = self.reflection.get_stats()
        yield f"\n[自主Agent] 任务完成 | 成功率: {stats['success_rate']}\n"

    def _classify_task(self, task: str) -> str:
        """任务分类"""
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["写代码", "编程", "函数", "代码"]):
            return "coding"
        elif any(kw in task_lower for kw in ["研究", "分析", "什么是", "解释"]):
            return "research"
        elif any(kw in task_lower for kw in ["监控", "系统", "cpu", "内存"]):
            return "monitor"
        elif any(kw in task_lower for kw in ["文件", "整理", "搜索"]):
            return "file"
        elif any(kw in task_lower for kw in ["清理", "备份", "自动"]):
            return "automation"
        return "general"

    def ask_myself(self, context: str) -> str:
        """自我提问：发现知识缺口"""
        prompt = f"""基于当前上下文，提出一个你无法回答的问题，说明你需要学习什么：

上下文: {context[:500]}

返回格式:
{{"question": "你的问题", "why_important": "为什么重要", "how_to_learn": "如何学习"}}"""

        response = self.assistant.chat(prompt)

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass

        return {"question": "", "why_important": "", "how_to_learn": ""}

    def get_status(self) -> str:
        """获取状态"""
        stats = self.reflection.get_stats()
        strategies = len(self.evolver.strategies.get("task_approaches", {}))
        patterns = len(self.evolver.strategies.get("learned_patterns", []))

        return f"""自主Agent状态:
- 任务统计: {stats}
- 已学策略: {strategies}种任务类型
- 已学模式: {patterns}个
- 当前计划: {len(self.current_plan)}步
- 最大迭代: {self.max_iterations}"""
