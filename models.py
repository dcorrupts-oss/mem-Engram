import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class Track(str, Enum):
    FACT = "FACT"
    EPISODIC = "EPISODIC"
    NOISE = "NOISE"


@dataclass
class EmotionDecayProfile:
    emotion_state: str = "NEUTRAL"

    WRITE_STRENGTH = {
        "HIGH": 1.2,
        "NEUTRAL": 1.0,
        "LOW": 1.15,
        "ANNOYED": 0.8,
    }

    DECAY_LAMBDA = {
        "HIGH": 0.008,
        "NEUTRAL": 0.010,
        "LOW": 0.006,
        "ANNOYED": 0.015,
    }

    @property
    def write_strength(self) -> float:
        return self.WRITE_STRENGTH.get(self.emotion_state, 1.0)

    @property
    def decay_lambda(self) -> float:
        return self.DECAY_LAMBDA.get(self.emotion_state, 0.010)


@dataclass
class EngramAtom:
    atom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    value: str = ""
    track: Track = Track.FACT
    primary_engram: str = "general"
    secondary_engrams: List[str] = field(default_factory=list)
    emotion: str = "NEUTRAL"
    emotion_intensity: float = 0.0
    created_at: float = field(default_factory=time.time)
    created_step: int = 0
    access_count: int = 0
    last_access_step: int = 0
    decay_lambda: float = 0.010
    write_strength: float = 1.0
    causal_parents: List[str] = field(default_factory=list)
    causal_children: List[str] = field(default_factory=list)

    @property
    def effective_resolution(self) -> float:
        if self.access_count == 0:
            return self.write_strength
        return self.write_strength * (1 + 0.15 * self.access_count)


@dataclass
class RoutingResult:
    emotion: str = "NEUTRAL"
    active_skills: List[str] = field(default_factory=list)
    write_scope: List[str] = field(default_factory=list)
    retrieved_atoms: List = field(default_factory=list)
    is_recall_query: bool = False
