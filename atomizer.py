import uuid
import time
import re
import logging
from typing import List, Optional, Callable

from models import EngramAtom, Track, EmotionDecayProfile

logger = logging.getLogger("mem-Engram.atomizer")

ALLOWED_KEYS = {
    "CHARACTER_NAME", "CHARACTER_TRAIT", "CHARACTER_GOAL", "CHARACTER_RELATION",
    "WORLD_RULE", "WORLD_LOCATION", "WORLD_FACTION", "WORLD_HISTORY",
    "PLOT_EVENT", "PLOT_CONFLICT", "PLOT_RESOLUTION",
    "USER_PREF", "USER_FACT", "EVENT",
    "CODE_SPEC", "CODE_PATTERN", "TASK_CONTEXT",
    "DATA_POINT", "HR_POLICY", "EMOTION_EVENT",
}

CAUSAL_PARENT_KEYS = {
    "CHARACTER_NAME", "WORLD_RULE", "PLOT_EVENT",
    "CODE_SPEC", "DATA_POINT",
}

LAMBDA_MAP = {
    "CHARACTER_NAME": 0.005,
    "CHARACTER_TRAIT": 0.008,
    "CHARACTER_GOAL": 0.010,
    "CHARACTER_RELATION": 0.012,
    "WORLD_RULE": 0.005,
    "WORLD_LOCATION": 0.008,
    "WORLD_FACTION": 0.010,
    "WORLD_HISTORY": 0.006,
    "PLOT_EVENT": 0.015,
    "PLOT_CONFLICT": 0.020,
    "PLOT_RESOLUTION": 0.025,
    "USER_PREF": 0.010,
    "USER_FACT": 0.008,
    "EVENT": 0.040,
    "CODE_SPEC": 0.003,
    "CODE_PATTERN": 0.005,
    "TASK_CONTEXT": 0.010,
    "DATA_POINT": 0.006,
    "HR_POLICY": 0.008,
    "EMOTION_EVENT": 0.012,
}

ENGram_KEY_MAP = {
    "CHARACTER_NAME": "character", "CHARACTER_TRAIT": "character",
    "CHARACTER_GOAL": "character", "CHARACTER_RELATION": "character",
    "WORLD_RULE": "worldbuilding", "WORLD_LOCATION": "worldbuilding",
    "WORLD_FACTION": "worldbuilding", "WORLD_HISTORY": "worldbuilding",
    "PLOT_EVENT": "narrative", "PLOT_CONFLICT": "narrative",
    "PLOT_RESOLUTION": "narrative",
    "USER_PREF": "general", "USER_FACT": "general",
    "EVENT": "general",
    "CODE_SPEC": "coding", "CODE_PATTERN": "coding",
    "TASK_CONTEXT": "general",
    "DATA_POINT": "data_analysis", "HR_POLICY": "hr_writing",
    "EMOTION_EVENT": "emotion",
}

CROSS_ENGRAM_KEYS = {
    "CHARACTER_RELATION", "PLOT_EVENT", "WORLD_FACTION",
    "TASK_CONTEXT", "EMOTION_EVENT",
}


class EmotionGate:
    EMOTION_KEYWORDS = {
        "HIGH": ["!", "太", "超", "极", "非常", "amazing", "wow", "love", "hate"],
        "LOW": ["...", "唉", "算了", "无所谓", "sigh", "whatever", "nevermind"],
        "ANNOYED": ["烦", "气死", "讨厌", "annoying", "stupid", "damn"],
    }

    def detect(self, text: str) -> str:
        text_lower = text.lower()
        for label, keywords in self.EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return label
        return "NEUTRAL"


class InformationRouter:
    _NOISE_PATTERNS = re.compile(
        r'^(嗯|啊|哦|ok|okay|好|是的|对|嗯嗯|哈哈|嘿嘿|\.+|…+|hm+|mm+|呃|那个|就是)$',
        re.IGNORECASE,
    )
    _FACT_SIGNALS = re.compile(
        r'(密码|账号|估值|利润|薪酬|项目|负责|过敏|叫|在|日期|截止|预算|'
        r'收入|成本|代码|漏洞|服务器|补丁|部署|上线|宕机|崩溃|'
        r'password|account|budget|revenue|cost|server|deploy|launch|crash|bug|'
        r'是|=|：|: \d|Q\d|v\d)',
        re.IGNORECASE,
    )
    _EPISODIC_SIGNALS = re.compile(
        r'(喜欢|讨厌|开心|难过|焦虑|压力|感觉|觉得|打算|想|希望|累|烦|'
        r'周末|今天|昨天|刚才|电影|吃饭|散步|天气|猫|狗|火锅|奶茶|'
        r'like|hate|feel|want|hope|tired|movie|dinner|walk|weather)',
        re.IGNORECASE,
    )

    def classify(self, text: str) -> str:
        text = text.strip()
        if not text or len(text) <= 2:
            return "NOISE"
        if self._NOISE_PATTERNS.match(text):
            return "NOISE"
        fact_score = len(self._FACT_SIGNALS.findall(text))
        episodic_score = len(self._EPISODIC_SIGNALS.findall(text))
        has_numbers = bool(re.search(r'\d{2,}', text))
        has_equals = "=" in text or "：" in text or ": " in text
        if fact_score >= 2 or (fact_score >= 1 and has_numbers) or has_equals:
            return "FACT"
        if episodic_score >= 1:
            return "EPISODIC"
        if fact_score >= 1:
            return "FACT"
        return "EPISODIC"


class EmotionAwareAtomizer:
    def __init__(
        self,
        emotion_gate: EmotionGate = None,
        info_router: InformationRouter = None,
        llm_extract_fn: Optional[Callable] = None,
    ):
        self.emotion_gate = emotion_gate or EmotionGate()
        self.info_router = info_router or InformationRouter()
        self.llm_extract_fn = llm_extract_fn

    def extract(
        self,
        raw_input: str,
        agent_id: str,
        current_step: int = 0,
        active_engrams: List[str] = None,
    ) -> List[EngramAtom]:
        category = self.info_router.classify(raw_input)
        if category == "NOISE":
            return []

        emotion = self.emotion_gate.detect(raw_input)
        decay_profile = EmotionDecayProfile(emotion_state=emotion)

        if category == "EPISODIC":
            return self._extract_episodic(raw_input, agent_id, current_step, decay_profile)
        return self._extract_fact(raw_input, agent_id, current_step, decay_profile, active_engrams)

    def _extract_episodic(
        self, raw_input: str, agent_id: str, current_step: int, decay_profile: EmotionDecayProfile
    ) -> List[EngramAtom]:
        atom = EngramAtom(
            key="EPISODIC_EVENT",
            value=raw_input[:200],
            track=Track.EPISODIC,
            primary_engram="general",
            secondary_engrams=["emotion"],
            emotion=decay_profile.emotion_state,
            emotion_intensity=decay_profile.write_strength,
            created_step=current_step,
            decay_lambda=decay_profile.decay_lambda,
            write_strength=decay_profile.write_strength,
        )
        return [atom]

    def _extract_fact(
        self, raw_input: str, agent_id: str, current_step: int,
        decay_profile: EmotionDecayProfile, active_engrams: List[str] = None,
    ) -> List[EngramAtom]:
        if self.llm_extract_fn:
            return self._llm_extract(raw_input, agent_id, current_step, decay_profile, active_engrams)
        return self._rule_extract(raw_input, agent_id, current_step, decay_profile, active_engrams)

    def _llm_extract(
        self, raw_input: str, agent_id: str, current_step: int,
        decay_profile: EmotionDecayProfile, active_engrams: List[str] = None,
    ) -> List[EngramAtom]:
        try:
            extracted = self.llm_extract_fn(raw_input)
            atoms = []
            for item in extracted:
                key = item.get("key", "USER_FACT")
                value = item.get("value", "")
                if key not in ALLOWED_KEYS or not value:
                    continue
                primary = ENGram_KEY_MAP.get(key, "general")
                secondary = []
                if key in CROSS_ENGRAM_KEYS:
                    secondary = [s for s in (active_engrams or []) if s != primary]
                atom = EngramAtom(
                    key=key,
                    value=value[:200],
                    track=Track.FACT,
                    primary_engram=primary,
                    secondary_engrams=secondary[:2],
                    emotion=decay_profile.emotion_state,
                    emotion_intensity=decay_profile.write_strength,
                    created_step=current_step,
                    decay_lambda=LAMBDA_MAP.get(key, 0.010),
                    write_strength=decay_profile.write_strength,
                )
                atoms.append(atom)
            return atoms
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return self._rule_extract(raw_input, agent_id, current_step, decay_profile, active_engrams)

    def _rule_extract(
        self, raw_input: str, agent_id: str, current_step: int,
        decay_profile: EmotionDecayProfile, active_engrams: List[str] = None,
    ) -> List[EngramAtom]:
        atoms = []
        if "=" in raw_input or "：" in raw_input:
            parts = raw_input.split("=", 1) if "=" in raw_input else raw_input.split("：", 1)
            if len(parts) == 2:
                key_part = parts[0].strip()
                value_part = parts[1].strip()
                if any(k in key_part.upper() for k in ["CODE", "SPEC", "RULE", "NORM"]):
                    key = "CODE_SPEC"
                elif any(k in key_part.upper() for k in ["DATA", "NUM", "COUNT", "Q"]):
                    key = "DATA_POINT"
                else:
                    key = "USER_FACT"
                primary = ENGram_KEY_MAP.get(key, "general")
                atom = EngramAtom(
                    key=key,
                    value=f"{key_part}={value_part}"[:200],
                    track=Track.FACT,
                    primary_engram=primary,
                    emotion=decay_profile.emotion_state,
                    emotion_intensity=decay_profile.write_strength,
                    created_step=current_step,
                    decay_lambda=LAMBDA_MAP.get(key, 0.010),
                    write_strength=decay_profile.write_strength,
                )
                atoms.append(atom)
        return atoms
