import re
import logging
from typing import List, Dict, Optional

from models import RoutingResult
from atom_store import EngramScopedStore
from retriever import EngramScopedRetriever

logger = logging.getLogger("mem-Engram.router")

DEFAULT_ENGRAM_KEYWORDS = {
    "character": ["角色", "人物", "主角", "性格", "character", "protagonist"],
    "worldbuilding": ["世界", "设定", "规则", "world", "setting", "rule"],
    "narrative": ["剧情", "故事", "情节", "narrative", "plot", "story"],
    "coding": ["代码", "编程", "函数", "code", "programming", "function", "api", "component"],
    "data_analysis": ["数据", "分析", "报表", "财务", "data", "analysis", "report", "financial", "metric"],
    "hr_writing": ["邮件", "人事", "hr", "email", "employee", "hire", "fire"],
    "emotion": ["情感", "情绪", "陪伴", "emotion", "feel", "mood", "companion"],
    "general": ["帮助", "问题", "怎么", "help", "question", "how"],
}


class EngramRouter:
    def __init__(self, engram_keywords: Dict[str, List[str]] = None):
        self.engram_keywords = engram_keywords or DEFAULT_ENGRAM_KEYWORDS

    def route(self, query: str) -> List[str]:
        query_lower = query.lower()
        scored = {}
        for engram, keywords in self.engram_keywords.items():
            score = 0
            for kw in keywords:
                if kw in query_lower:
                    score += 1
            if score > 0:
                scored[engram] = score
        if not scored:
            return ["general"]
        sorted_engrams = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        top_engram = sorted_engrams[0][0]
        result = [top_engram]
        for engram, score in sorted_engrams[1:]:
            if score >= sorted_engrams[0][1] * 0.5:
                result.append(engram)
        return result[:3]


class ThreePhaseRouter:
    def __init__(
        self,
        engram_router: EngramRouter = None,
        emotion_gate=None,
        atom_store: EngramScopedStore = None,
        retriever: EngramScopedRetriever = None,
        llm_client=None,
    ):
        self.engram_router = engram_router or EngramRouter()
        self.emotion_gate = emotion_gate
        self.atom_store = atom_store
        self.retriever = retriever
        self.llm_client = llm_client

    def route(
        self,
        user_input: str,
        agent_id: str,
        current_step: int = 0,
    ) -> RoutingResult:
        emotion = self._detect_emotion(user_input)
        active_engrams = self.engram_router.route(user_input)
        is_recall = self._is_recall_query(user_input)
        retrieved = []
        if self.retriever and self.atom_store:
            retrieved = self.retriever.retrieve_with_scope(
                query=user_input,
                agent_id=agent_id,
                candidate_scopes=active_engrams,
                top_k=15,
                current_step=current_step,
            )
        return RoutingResult(
            emotion=emotion,
            active_skills=active_engrams,
            write_scope=active_engrams,
            retrieved_atoms=retrieved,
            is_recall_query=is_recall,
        )

    def _detect_emotion(self, text: str) -> str:
        if self.emotion_gate:
            return self.emotion_gate.detect(text)
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["!", "太", "超", "amazing", "wow"]):
            return "HIGH"
        if any(kw in text_lower for kw in ["...", "唉", "算了", "sigh"]):
            return "LOW"
        return "NEUTRAL"

    def _is_recall_query(self, query: str) -> bool:
        recall_patterns = [r"你还记得", r"之前.*说过", r"上次.*提到", r"帮我回忆", r"回忆一下"]
        for pattern in recall_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
