"""
Agent - 自主推理和任务执行
支持两种模式：
1. Orchestrator 模式：路由到专门 Agent
2. Autonomous 模式：全自主思考-行动-观察-进化
"""

import json
import sys
import os
import logging
from typing import Generator, List, Dict, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.assistant import VoiceAssistant
from core.memory_manager import get_memory_manager
from core.orchestrator import Orchestrator
from config import config

logger = logging.getLogger(__name__)


class Agent:
    """
    自主 Agent - 支持编排模式和全自主模式
    """

    def __init__(self, autonomous: bool = False):
        self.assistant = VoiceAssistant()
        self.memory = get_memory_manager()
        self.autonomous = autonomous
        self.task_history = []
        self.current_task = None
        self.max_iterations = 10
        self.max_retries = 3

        # 初始化编排器
        self.orchestrator = Orchestrator()
        self._register_agents()

    def _register_agents(self):
        """注册所有专门 Agent"""
        try:
            from core.agents.coding_agent import coding_agent
            from core.agents.research_agent import research_agent
            from core.agents.monitor_agent import monitor_agent
            from core.agents.automation_agent import automation_agent
            from core.agents.file_agent import file_agent
            from core.agents.learning_agent import learning_agent

            # 给需要 LLM 的 Agent 注入客户端
            coding_agent.llm = self.assistant.ollama_client
            coding_agent.llm._model = self.assistant.ollama_model
            research_agent.llm = self.assistant.ollama_client
            research_agent.llm._model = self.assistant.ollama_model

            # 注册到编排器
            for agent in [coding_agent, research_agent, monitor_agent,
                          automation_agent, file_agent, learning_agent]:
                self.orchestrator.register(agent)

            logger.info(f"已注册 {len(self.orchestrator.agents)} 个 Agent")
        except ImportError as e:
            logger.warning(f"部分 Agent 加载失败: {e}")

    def think(self, context: str, question: str) -> str:
        """思考：分析当前情况，决定下一步"""
        prompt = f"""你是一个智能助手，正在执行任务。

当前上下文：
{context}

问题：{question}

请分析当前情况，决定下一步应该做什么。
只返回你的思考过程和决定，不要执行任何操作。"""
        return self.assistant.chat(prompt)

    def act(self, action: str, params: dict = None) -> str:
        """行动：执行具体操作"""
        if params:
            action_with_params = f"{action}\n参数: {json.dumps(params, ensure_ascii=False)}"
        else:
            action_with_params = action
        return self.assistant.chat(action_with_params)

    def reflect(self, action: str, result: str, goal: str) -> Dict[str, Any]:
        """反思：评估结果，决定是否继续"""
        prompt = f"""你是一个智能助手，正在反思任务执行结果。

目标：{goal}
执行的操作：{action}
执行结果：{result}

请评估：
1. 这个结果是否达到了目标？
2. 如果没有，问题是什么？
3. 下一步应该做什么？

返回JSON格式：
{{"success": true/false, "reason": "原因说明", "next_action": "下一步操作（如果需要）", "next_params": {{}}}}"""

        response = self.assistant.chat(prompt)

        try:
            import re
            # 清理 markdown 代码块
            cleaned = re.sub(r'```json\s*', '', response)
            cleaned = re.sub(r'```\s*', '', cleaned)
            try:
                return json.loads(cleaned.strip())
            except json.JSONDecodeError:
                pass
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"反思解析失败: {e}")

        return {
            "success": True,
            "reason": "无法解析反思结果",
            "next_action": None,
            "next_params": {}
        }

    def run_task(self, user_request: str) -> Generator[str, None, None]:
        """
        执行任务：
        - autonomous=True: 全自主模式（思考-行动-观察-进化）
        - autonomous=False: 编排模式（路由到专门 Agent）
        """
        # 记录任务
        self.current_task = {
            "request": user_request,
            "start_time": datetime.now().isoformat(),
            "steps": [],
        }

        if self.autonomous:
            # 全自主模式
            from core.autonomous_agent import AutonomousAgent
            auto = AutonomousAgent(self.assistant, self.orchestrator)
            for chunk in auto.solve(user_request):
                yield chunk
            self.current_task["steps"].append({"mode": "autonomous"})
        else:
            # 编排模式
            yield f"[Agent] 分析任务: {user_request}\n"

            result = self.orchestrator.execute(user_request, context={
                "memory": self.memory.get_context_for_llm(user_request),
            })

            if result.content:
                yield f"[{result.agent_name}] {result.content}\n"
                self.current_task["steps"].append({
                    "agent": result.agent_name,
                    "success": result.success,
                })
            else:
                yield "[Agent] 使用通用模式回复...\n"
                for chunk in self.assistant.stream_with_tools(user_request):
                    yield chunk

        # 任务完成
        self.current_task["end_time"] = datetime.now().isoformat()
        self.task_history.append(self.current_task)
        self.memory.add_memory(
            f"完成任务: {user_request}",
            memory_type="task",
            metadata={"mode": "autonomous" if self.autonomous else "orchestrator"},
        )

        yield f"\n[Agent] 任务完成\n"

    def run_simple(self, user_input: str) -> Generator[str, None, None]:
        """简单模式（直接用 LLM）"""
        for chunk in self.assistant.stream_with_tools(user_input):
            yield chunk

    def chat(self, user_input: str) -> str:
        """简单对话"""
        return self.assistant.chat(user_input)

    def get_status(self) -> str:
        """获取 Agent 状态"""
        agents = self.orchestrator.list_agents()
        agent_names = ", ".join(a["name"] for a in agents)
        mode = "全自主" if self.autonomous else "编排"
        return f"""Agent状态:
- 模式: {mode}
- 模型: {self.assistant.current_model}
- 已注册Agent: {len(agents)}个 ({agent_names})
- 任务历史: {len(self.task_history)}个
- 最大迭代: {self.max_iterations}
- 编排器统计: {self.orchestrator.get_stats()}"""


def main():
    """测试 Agent"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="全自主模式")
    args = parser.parse_args()

    agent = Agent(autonomous=args.auto)
    print(agent.get_status())
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Goodbye!")
            break
        if user_input.lower() == "status":
            print(agent.get_status())
            continue
        if user_input.lower() == "auto":
            agent.autonomous = not agent.autonomous
            print(f"[模式切换] {'全自主' if agent.autonomous else '编排'}")
            continue

        print("Agent: ", end="", flush=True)
        for chunk in agent.run_task(user_input):
            print(chunk, end="", flush=True)
        print()


if __name__ == "__main__":
    main()
