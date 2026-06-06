"""
Orchestrator - 多 Agent 编排器
负责任务分析、Agent 路由、结果汇总
"""

import logging
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime

from core.agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    多 Agent 编排器
    - 接收用户请求
    - 评估各 Agent 置信度
    - 路由到最合适的 Agent
    - 复杂任务拆分后分配给多个 Agent
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.execution_history: List[Dict[str, Any]] = []

    def register(self, agent):
        """注册 Agent（兼容 BaseAgent 和旧式 Agent）"""
        name = getattr(agent, 'name', agent.__class__.__name__.lower().replace('agent', ''))
        agent.name = name
        if not hasattr(agent, 'description'):
            agent.description = agent.__class__.__name__
        if not hasattr(agent, 'capabilities'):
            agent.capabilities = []
        self.agents[name] = agent
        logger.info(f"注册 Agent: {name} ({agent.description})")

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有已注册 Agent"""
        return [
            {
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
            }
            for a in self.agents.values()
        ]

    def route(self, task: str) -> tuple[BaseAgent, float]:
        """
        评估所有 Agent，返回最合适的 Agent 和置信度
        """
        best_agent = None
        best_score = 0.0

        for agent in self.agents.values():
            try:
                if not hasattr(agent, 'can_handle'):
                    continue
                score = agent.can_handle(task)
                if score > best_score:
                    best_score = score
                    best_agent = agent
            except Exception as e:
                logger.warning(f"Agent {getattr(agent, 'name', '?')} 置信度评估失败: {e}")

        return best_agent, best_score

    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        执行任务：路由到最佳 Agent 并执行
        """
        context = context or {}
        start_time = datetime.now()

        # 路由
        agent, confidence = self.route(task)

        if not agent or confidence < 0.3:
            # 没有合适的 Agent，返回通用回复
            logger.info(f"无合适 Agent (最高置信度 {confidence:.2f})，使用通用回复")
            return AgentResult(
                agent_name="orchestrator",
                success=True,
                content="",  # 空字符串表示应由上层 LLM 直接回复
                metadata={"confidence": confidence, "routed": False},
            )

        agent_name = getattr(agent, 'name', 'unknown')
        logger.info(f"路由到 {agent_name} (置信度 {confidence:.2f})")

        # 执行
        try:
            if hasattr(agent, 'run'):
                result = agent.run(task, context)
            else:
                result = AgentResult(
                    agent_name=agent_name,
                    success=False,
                    content=f"Agent {agent_name} 没有 run 方法",
                )
        except Exception as e:
            logger.error(f"Agent {agent_name} 执行异常: {e}")
            result = AgentResult(
                agent_name=agent_name,
                success=False,
                content=f"执行出错: {e}",
                metadata={"error": str(e)},
            )

        # 记录
        elapsed = (datetime.now() - start_time).total_seconds()
        self.execution_history.append({
            "task": task[:200],
            "agent": agent.name,
            "confidence": confidence,
            "success": result.success,
            "elapsed": elapsed,
            "timestamp": datetime.now().isoformat(),
        })

        return result

    def execute_multi(self, task: str, context: Dict[str, Any] = None) -> List[AgentResult]:
        """
        复杂任务：拆分为子任务，分配给多个 Agent
        """
        context = context or {}
        results = []

        # 评估所有 Agent 的置信度
        scores = []
        for agent in self.agents.values():
            try:
                score = agent.can_handle(task)
                if score > 0.3:
                    scores.append((agent, score))
            except Exception:
                pass

        # 按置信度排序，取前 3 个
        scores.sort(key=lambda x: x[1], reverse=True)
        top_agents = scores[:3]

        if not top_agents:
            return [AgentResult(
                agent_name="orchestrator",
                success=True,
                content="",
                metadata={"no_agent": True},
            )]

        # 并行执行（串行模拟）
        for agent, score in top_agents:
            try:
                result = agent.run(task, context)
                results.append(result)
            except Exception as e:
                results.append(AgentResult(
                    agent_name=agent.name,
                    success=False,
                    content=str(e),
                ))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取编排器统计"""
        total = len(self.execution_history)
        success = sum(1 for h in self.execution_history if h["success"])
        agents_used = set(h["agent"] for h in self.execution_history)

        return {
            "total_tasks": total,
            "success_rate": f"{success/total*100:.0f}%" if total else "N/A",
            "agents_used": list(agents_used),
            "registered_agents": len(self.agents),
        }
