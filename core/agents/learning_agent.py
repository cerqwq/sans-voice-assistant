"""
学习Agent - 习惯学习、偏好记忆、个性化推荐
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter


class LearningAgent:
    """学习Agent - 学习用户习惯并提供个性化服务"""

    def __init__(self, memory_path: str = None):
        self.memory_path = memory_path or os.path.expanduser("~/.sans/learning.json")
        self.user_profile = self._load_profile()
        self.interaction_history = []

    def _load_profile(self) -> Dict[str, Any]:
        """加载用户画像"""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "preferences": {},
            "habits": {},
            "interests": [],
            "interaction_patterns": {},
            "last_updated": None
        }

    def _save_profile(self):
        """保存用户画像"""
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        self.user_profile["last_updated"] = datetime.now().isoformat()

        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.user_profile, f, ensure_ascii=False, indent=2)

    def record_interaction(self, interaction_type: str, content: str, metadata: Dict = None):
        """记录用户交互"""
        interaction = {
            "type": interaction_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.interaction_history.append(interaction)

        # 更新用户画像
        self._update_profile_from_interaction(interaction)

        # 定期保存
        if len(self.interaction_history) % 10 == 0:
            self._save_profile()

    def _update_profile_from_interaction(self, interaction: Dict):
        """从交互中更新用户画像"""
        # 更新交互模式
        patterns = self.user_profile.setdefault("interaction_patterns", {})
        hour = datetime.now().hour
        time_slot = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        patterns[time_slot] = patterns.get(time_slot, 0) + 1

        # 更新兴趣
        content = interaction.get("content", "").lower()
        keywords = self._extract_keywords(content)
        interests = self.user_profile.setdefault("interests", [])
        for kw in keywords:
            if kw not in interests:
                interests.append(kw)
                # 只保留最近的20个兴趣
                if len(interests) > 20:
                    interests.pop(0)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取中文词汇
        import re
        # 去除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        # 分词（简单按空格和常见分隔符）
        words = re.split(r'[\s,，。！？、]+', text)
        # 过滤太短的词
        return [w for w in words if len(w) >= 2][:5]

    def get_user_preferences(self) -> Dict[str, Any]:
        """获取用户偏好"""
        return self.user_profile.get("preferences", {})

    def update_preference(self, key: str, value: Any):
        """更新用户偏好"""
        self.user_profile.setdefault("preferences", {})[key] = value
        self._save_profile()

    def get_habits(self) -> Dict[str, Any]:
        """获取用户习惯"""
        return self.user_profile.get("habits", {})

    def record_habit(self, habit_name: str, details: Dict = None):
        """记录用户习惯"""
        habits = self.user_profile.setdefault("habits", {})
        if habit_name not in habits:
            habits[habit_name] = {
                "first_seen": datetime.now().isoformat(),
                "count": 0,
                "details": details or {}
            }

        habits[habit_name]["count"] += 1
        habits[habit_name]["last_seen"] = datetime.now().isoformat()
        self._save_profile()

    def get_recommendations(self, context: str = "") -> List[str]:
        """根据用户画像提供推荐"""
        recommendations = []

        # 基于兴趣推荐
        interests = self.user_profile.get("interests", [])
        if interests:
            recommendations.append(f"基于您的兴趣，您可能喜欢: {', '.join(interests[:3])}")

        # 基于习惯推荐
        habits = self.user_profile.get("habits", {})
        if habits:
            frequent_habits = sorted(habits.items(), key=lambda x: x[1].get("count", 0), reverse=True)
            if frequent_habits:
                recommendations.append(f"您经常做: {frequent_habits[0][0]}")

        # 基于时间推荐
        hour = datetime.now().hour
        patterns = self.user_profile.get("interaction_patterns", {})
        if hour < 12 and patterns.get("morning", 0) > 5:
            recommendations.append("早上好！您通常在这个时间段活跃")
        elif hour >= 18 and patterns.get("evening", 0) > 5:
            recommendations.append("晚上好！需要我帮您放松一下吗？")

        return recommendations if recommendations else ["暂无推荐，继续使用我会学习您的习惯"]

    def predict_next_action(self, current_context: str) -> Optional[str]:
        """预测用户下一步可能的操作"""
        # 简单实现：基于历史模式
        patterns = self.user_profile.get("interaction_patterns", {})
        if not patterns:
            return None

        # 找到最活跃的时间段
        most_active = max(patterns.items(), key=lambda x: x[1])
        return f"您通常在{most_active[0]}最活跃"

    def get_learning_summary(self) -> Dict[str, Any]:
        """获取学习总结"""
        return {
            "total_interactions": len(self.interaction_history),
            "interests_count": len(self.user_profile.get("interests", [])),
            "habits_count": len(self.user_profile.get("habits", {})),
            "preferences_count": len(self.user_profile.get("preferences", {})),
            "most_active_time": self._get_most_active_time(),
            "last_updated": self.user_profile.get("last_updated")
        }

    def _get_most_active_time(self) -> str:
        """获取最活跃时间段"""
        patterns = self.user_profile.get("interaction_patterns", {})
        if not patterns:
            return "未知"
        return max(patterns.items(), key=lambda x: x[1])[0]


# 创建全局实例
learning_agent = LearningAgent()
