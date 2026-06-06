"""
记忆管理器 - 支持语义检索和长期记忆
使用ChromaDB进行向量存储和检索
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

MEMORY_PATH = Path(__file__).parent.parent / "memory" / "user_memory.json"
CHROMA_PATH = Path(__file__).parent.parent / "memory" / "chroma_db"


class MemoryManager:
    """记忆管理器 - 支持语义检索"""

    def __init__(self):
        self.memory = self._load()
        self.chroma_client = None
        self.collection = None
        self._init_chroma()

    def _load(self) -> dict:
        if MEMORY_PATH.exists():
            with open(MEMORY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "user_name": "",
            "preferences": {"language": "zh", "reply_style": "简洁", "likes": [], "dislikes": []},
            "habits": {"common_commands": [], "wake_word_variants": [], "active_hours": "", "location": ""},
            "conversation_history": {"topics_discussed": [], "tools_used": {}, "last_interaction": ""},
            "personal_notes": [],
            "facts": [],
        }

    def _save(self):
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def _init_chroma(self):
        """初始化ChromaDB"""
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            self.collection = self.chroma_client.get_or_create_collection(
                name="memory",
                metadata={"hnsw:space": "cosine"}
            )
            print("[Memory] ChromaDB初始化成功")
        except ImportError:
            print("[Memory] ChromaDB未安装，使用简单记忆模式")
        except Exception as e:
            print(f"[Memory] ChromaDB初始化失败: {e}")

    def add_memory(self, content: str, memory_type: str = "fact", metadata: dict = None):
        """添加记忆到向量数据库"""
        # 添加到简单记忆
        if memory_type == "fact":
            self.memory.setdefault("facts", []).append({
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })
        elif memory_type == "note":
            self.memory.setdefault("personal_notes", []).append(content)

        # 添加到ChromaDB
        if self.collection:
            try:
                doc_id = f"memory_{datetime.now().timestamp()}"
                self.collection.add(
                    documents=[content],
                    ids=[doc_id],
                    metadatas=[{
                        "type": memory_type,
                        "timestamp": datetime.now().isoformat(),
                        **(metadata or {}),
                    }]
                )
            except Exception as e:
                print(f"ChromaDB添加失败: {e}")

        self._save()

    def search_memory(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """语义搜索记忆"""
        if not self.collection:
            # 简单搜索（无ChromaDB时）
            results = []
            for fact in self.memory.get("facts", []):
                if query.lower() in fact["content"].lower():
                    results.append({"content": fact["content"], "score": 1.0})
            return results[:n_results]

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return [
                {"content": doc, "score": score}
                for doc, score in zip(results["documents"][0], results["distances"][0])
            ]
        except Exception as e:
            print(f"ChromaDB搜索失败: {e}")
            return []

    def get_system_prompt_with_memory(self, base_prompt: str) -> str:
        """将记忆注入系统提示"""
        parts = []
        name = self.memory.get("user_name", "")
        if name:
            parts.append(f"用户名字: {name}")

        prefs = self.memory.get("preferences", {})
        if prefs.get("likes"):
            parts.append(f"喜好: {', '.join(prefs['likes'][-5:])}")
        if prefs.get("dislikes"):
            parts.append(f"不喜欢: {', '.join(prefs['dislikes'][-5:])}")

        notes = self.memory.get("personal_notes", [])
        if notes:
            parts.append(f"备注: {'; '.join(notes[-3:])}")

        if parts:
            return base_prompt + "\n[记忆] " + " | ".join(parts)
        return base_prompt

    def update_from_conversation(self, user_text: str, assistant_text: str):
        """从对话中提取信息并更新记忆"""
        changed = False

        # 检测名字
        for pattern in ["我叫", "我是", "叫我", "我的名字是"]:
            if pattern in user_text:
                idx = user_text.find(pattern) + len(pattern)
                rest = user_text[idx:].strip()
                name = re.split(r'[，。！？,\s]', rest)[0]
                if name and 1 <= len(name) <= 10:
                    self.memory["user_name"] = name
                    changed = True
                    break

        # 检测喜好
        for pattern in ["我喜欢", "我爱", "我超喜欢", "我最喜欢"]:
            if pattern in user_text:
                idx = user_text.find(pattern) + len(pattern)
                rest = user_text[idx:].strip()
                item = re.split(r'[，。！？,\s]', rest)[0]
                if item and len(item) <= 15:
                    likes = self.memory.setdefault("preferences", {}).setdefault("likes", [])
                    if item not in likes:
                        likes.append(item)
                        changed = True

        # 检测不喜欢
        for pattern in ["我不喜欢", "我讨厌", "我不爱"]:
            if pattern in user_text:
                idx = user_text.find(pattern) + len(pattern)
                rest = user_text[idx:].strip()
                item = re.split(r'[，。！？,\s]', rest)[0]
                if item and len(item) <= 15:
                    dislikes = self.memory.setdefault("preferences", {}).setdefault("dislikes", [])
                    if item not in dislikes:
                        dislikes.append(item)
                        changed = True

        # 更新最后对话时间
        self.memory.setdefault("conversation_history", {})["last_interaction"] = \
            datetime.now().isoformat()

        if changed:
            self._save()

    def get_context_for_llm(self, query: str = "") -> str:
        """获取用于LLM的上下文信息"""
        parts = []

        # 用户信息
        user_info = self.get_user_info()
        if user_info:
            parts.append(f"[用户信息]\n{user_info}")

        # 相关记忆（语义检索）
        if query:
            related = self.search_memory(query, n_results=3)
            if related:
                memories = [r["content"] for r in related]
                parts.append(f"[相关记忆]\n" + "\n".join(memories))

        return "\n\n".join(parts) if parts else ""

    def get_user_info(self) -> str:
        """获取用户信息摘要"""
        parts = []
        if self.memory.get("user_name"):
            parts.append(f"用户名: {self.memory['user_name']}")
        if self.memory.get("preferences", {}).get("likes"):
            parts.append(f"喜好: {', '.join(self.memory['preferences']['likes'])}")
        if self.memory.get("preferences", {}).get("dislikes"):
            parts.append(f"不喜欢: {', '.join(self.memory['preferences']['dislikes'])}")
        if self.memory.get("personal_notes"):
            parts.append(f"备注: {', '.join(self.memory['personal_notes'][-3:])}")
        return "\n".join(parts) if parts else "暂无用户信息"


# 全局记忆管理器实例
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """获取全局记忆管理器"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
