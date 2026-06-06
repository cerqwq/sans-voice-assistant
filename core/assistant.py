"""
Voice Assistant - Hybrid Model Architecture
Simple tasks: Local Ollama (qwen3:4b)
Complex tasks: Claude API (claude-sonnet-4-6)
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

from core.tool_registry import create_default_registry
from core.memory_manager import get_memory_manager
from config import config

# 复杂任务关键词（需要具体动词，不要用"帮我"这种泛词）
COMPLEX_KEYWORDS = [
    "分析", "总结", "翻译", "解释", "比较", "评估", "设计", "规划",
    "优化", "重构", "调试", "写代码", "写程序", "写文章", "写报告",
    "帮我写", "帮我做", "帮我创建", "帮我分析", "帮我优化",
    "calculate", "analyze", "summarize", "translate", "explain",
    "compare", "evaluate", "design", "plan", "optimize", "refactor",
    "debug", "write code", "create", "generate", "implement",
]


def _is_complex_task(text: str) -> bool:
    """判断是否为复杂任务"""
    text_lower = text.lower()

    # 检查关键词
    for keyword in COMPLEX_KEYWORDS:
        if keyword in text_lower:
            return True

    # 长文本通常是复杂任务
    if len(text) > 200:
        return True

    # 包含代码相关
    code_indicators = ["```", "def ", "class ", "import ", "function ", "var ", "const "]
    for indicator in code_indicators:
        if indicator in text:
            return True

    return False


class VoiceAssistant:
    """
    Voice assistant with hybrid model architecture.
    - Simple tasks: Local Ollama (qwen3:4b) - fast, free
    - Complex tasks: Claude API (claude-sonnet-4-6) - powerful, paid
    """

    def __init__(self, model: str = None, system_prompt: str = None):
        # Ollama客户端（本地，免费）
        self.ollama_client = OpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama",
        )
        self.ollama_model = config.ollama_model

        # MIMO客户端（云端，用于复杂任务）
        self.mimo_client = None
        if config.mimo_api_key:
            self.mimo_client = OpenAI(
                base_url=config.mimo_base_url,
                api_key=config.mimo_api_key,
            )
        self.mimo_model = config.mimo_model

        # Claude客户端（备用）
        self.claude_client = None
        if config.anthropic_api_key:
            self.claude_client = OpenAI(
                base_url=config.anthropic_base_url or "https://api.anthropic.com/v1",
                api_key=config.anthropic_api_key,
            )
        self.claude_model = config.claude_model

        # 当前使用的模型
        self.current_model = "ollama"
        self.registry = create_default_registry()
        self.messages = []
        self.system_prompt = system_prompt or config.system_prompt
        # 使用统一的记忆管理器
        self.memory_manager = get_memory_manager()
        # Ollama可用性缓存
        self._ollama_available = None
        self._ollama_check_time = 0
        self._ollama_cache_ttl = 60  # 缓存60秒

    def _select_model(self, user_message: str) -> str:
        """根据任务复杂度选择模型（智能判断）"""
        # 如果没有MIMO或Claude API密钥，只能用Ollama
        if not self.mimo_client and not self.claude_client:
            return "ollama"

        # 快速规则判断（明显的复杂任务）
        if _is_complex_task(user_message):
            if self.mimo_client:
                return "mimo"
            elif self.claude_client:
                return "claude"

        # 简单任务：优先Ollama，如果不可用则用MIMO
        if config.use_claude_for_complex:
            # 使用缓存的Ollama状态
            if self._is_ollama_available():
                return "ollama"

            # Ollama不可用，使用MIMO
            if self.mimo_client:
                return "mimo"
            elif self.claude_client:
                return "claude"

        return "ollama"

    def _is_ollama_available(self) -> bool:
        """检查Ollama是否可用（带缓存）"""
        import time
        current_time = time.time()

        # 如果缓存有效，直接返回
        if (self._ollama_available is not None and
            current_time - self._ollama_check_time < self._ollama_cache_ttl):
            return self._ollama_available

        # 检查Ollama状态
        try:
            import requests
            response = requests.get(config.ollama_base_url.replace('/v1', '/api/tags'), timeout=2)
            self._ollama_available = response.status_code == 200
        except Exception:
            self._ollama_available = False

        self._ollama_check_time = current_time
        return self._ollama_available

    def _is_complex_task_smart(self, user_message: str) -> bool:
        """使用LLM智能判断任务复杂度（备用方法）"""
        # 这个方法可以在需要时调用，但会增加一次API调用
        # 当前使用规则判断，未来可以集成
        return _is_complex_task(user_message)

    def _get_client_and_model(self, user_message: str):
        """获取对应的客户端和模型"""
        selected = self._select_model(user_message)
        self.current_model = selected

        if selected == "mimo":
            return self.mimo_client, self.mimo_model, config.claude_max_tokens
        elif selected == "claude":
            return self.claude_client, self.claude_model, config.claude_max_tokens
        else:
            return self.ollama_client, self.ollama_model, config.ollama_max_tokens

    def chat(self, user_message: str) -> str:
        """
        Non-streaming chat with tool calling support.
        Returns final text response after all tool calls are resolved.
        """
        self.messages.append({"role": "user", "content": user_message})

        # Build tools config for OpenAI format
        tools = self._get_openai_tools()
        sys_prompt = self._get_system_prompt_with_memory()

        # 选择模型
        client, model, max_tokens = self._get_client_and_model(user_message)
        logger.info(f"  [Model] Using {self.current_model}: {model}")

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": sys_prompt}] + self.messages,
            tools=tools if tools else None,
            extra_body={"think": False} if self.current_model == "ollama" else None,
        )

        message = response.choices[0].message

        # Process tool calls in a loop
        iterations = 0
        while message.tool_calls and iterations < 10:
            iterations += 1
            self.messages.append(message)

            for tool_call in message.tool_calls:
                func = tool_call.function
                logger.info(f"  [Tool] {func.name}({func.arguments})")
                args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                result = self.registry.execute(func.name, args)

                preview = result["content"][:100]
                prefix = "  [Error]" if result.get("is_error") else "  [Result]"
                logger.info(f"{prefix} {preview}")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result["content"],
                })

            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": sys_prompt}] + self.messages,
                tools=tools if tools else None,
                extra_body={"think": False} if self.current_model == "ollama" else None,
            )
            message = response.choices[0].message

        # Extract text
        final_text = message.content or ""
        self.messages.append({"role": "assistant", "content": final_text})

        # 更新记忆
        self._update_memory_from_text(user_message, final_text)

        return final_text

    def _get_openai_tools(self):
        """Convert tool definitions to OpenAI format."""
        tools = self.registry.get_tool_definitions()
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("input_schema", {}),
                }
            })
        return openai_tools

    def stream_response(self, user_message: str):
        """
        Streaming chat (no tool calling).
        Yields text chunks for TTS integration.
        Use this for voice output - lower latency.
        """
        self.messages.append({"role": "user", "content": user_message})
        sys_prompt = self._get_system_prompt_with_memory()

        # 选择模型
        client, model, max_tokens = self._get_client_and_model(user_message)

        try:
            stream = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": sys_prompt}] + self.messages,
                stream=True,
                extra_body={"think": False} if self.current_model == "ollama" else None,
            )

            full_response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text

            self.messages.append({"role": "assistant", "content": full_response})
            self._update_memory_from_text(user_message, full_response)
        except Exception as e:
            error_msg = f"抱歉，出了点问题：{e}"
            yield error_msg
            self.messages.append({"role": "assistant", "content": error_msg})

    def _is_simple_greeting(self, text: str) -> bool:
        """判断是否为简单问候，无需工具调用"""
        greetings = ["你好", "hi", "hello", "嘿", "嗨", "早上好", "晚上好", "下午好", "晚安", "再见", "拜拜"]
        text_lower = text.lower().strip()
        return any(g in text_lower for g in greetings) and len(text) < 20

    def stream_with_tools(self, user_message: str):
        """
        Streaming chat WITH tool calling support.
        First checks if tools are needed, executes them, then streams the final response.

        This is the ideal mode for voice: tools are executed, then the summary is streamed.
        """
        self.messages.append({"role": "user", "content": user_message})
        sys_prompt = self._get_system_prompt_with_memory()

        # 简单问候直接回复，不调用工具
        if self._is_simple_greeting(user_message):
            client, model, max_tokens = self._get_client_and_model(user_message)
            logger.info(f"  [Model] Using {self.current_model}: {model} (simple)")
            stream = client.chat.completions.create(
                model=model,
                max_tokens=200,  # 简单回复用更少token
                messages=[{"role": "system", "content": sys_prompt}] + self.messages,
                stream=True,
                extra_body={"think": False} if self.current_model == "ollama" else None,
            )
            full_response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text
            self.messages.append({"role": "assistant", "content": full_response})
            self._update_memory_from_text(user_message, full_response)
            return

        tools = self._get_openai_tools()

        # 选择模型
        client, model, max_tokens = self._get_client_and_model(user_message)
        logger.info(f"  [Model] Using {self.current_model}: {model}")

        # First call: check if tools are needed
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": sys_prompt}] + self.messages,
            tools=tools if tools else None,
            extra_body={"think": False} if self.current_model == "ollama" else None,
        )

        message = response.choices[0].message

        # If tools are needed, execute them first
        iterations = 0
        while message.tool_calls and iterations < 10:
            iterations += 1
            self.messages.append(message)

            for tool_call in message.tool_calls:
                func = tool_call.function
                yield f"[工具] {func.name}...\n"
                args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                result = self.registry.execute(func.name, args)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result["content"],
                })

            # Next call
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": sys_prompt}] + self.messages,
                tools=tools if tools else None,
                extra_body={"think": False} if self.current_model == "ollama" else None,
            )
            message = response.choices[0].message

        # Now stream the final text response
        # Remove the last assistant message to re-stream it
        if self.messages and self.messages[-1]["role"] == "assistant":
            self.messages.pop()

        stream = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": sys_prompt}] + self.messages,
            stream=True,
            extra_body={"think": False} if self.current_model == "ollama" else None,
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        self.messages.append({"role": "assistant", "content": full_response})
        self._update_memory_from_text(user_message, full_response)

    def _get_system_prompt_with_memory(self) -> str:
        """生成包含记忆的系统提示"""
        return self.memory_manager.get_system_prompt_with_memory(self.system_prompt)

    def _update_memory_from_text(self, user_text: str, assistant_text: str):
        """从对话中提取信息更新记忆"""
        self.memory_manager.update_from_conversation(user_text, assistant_text)

    def reset(self):
        """Clear conversation history."""
        self.messages = []

    def trim_history(self):
        """Trim conversation history to max turns."""
        max_msgs = config.max_history_turns * 2
        if len(self.messages) > max_msgs:
            self.messages = self.messages[-max_msgs:]

    def get_tools_summary(self) -> str:
        """Return a summary of available tools."""
        tools = self.registry.get_tool_definitions()
        summary = f"可用工具 ({len(tools)}):\n"
        for t in tools:
            desc = t['description'][:60]
            summary += f"  • {t['name']}: {desc}...\n"
        return summary

    def get_model_info(self) -> str:
        """获取当前模型信息"""
        cloud_model = self.mimo_model if self.mimo_client else (self.claude_model if self.claude_client else '未配置')
        return f"本地模型: {self.ollama_model}\n云端模型: {cloud_model}\n当前使用: {self.current_model}"


def main():
    """Interactive text mode with tool support."""
    print("=" * 50)
    print("  Sans Voice Assistant (Agent Mode)")
    print("  Type 'quit' to exit, 'reset' to clear history")
    print("=" * 50)
    print()

    try:
        assistant = VoiceAssistant()
        print(assistant.get_tools_summary())
        print(assistant.get_model_info())
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
            if user_input.lower() == "reset":
                assistant.reset()
                print("[History cleared]\n")
                continue

            # Use streaming with tools for best experience
            print("Sans: ", end="", flush=True)
            for chunk in assistant.stream_with_tools(user_input):
                print(chunk, end="", flush=True)
            print("\n")

            assistant.trim_history()

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ANTHROPIC_API_KEY is set in .env or environment.")


if __name__ == "__main__":
    main()
