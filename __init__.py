"""
mem-Engram: Cognitive-Scoped Memory Architecture
Engram-AI Commercial Brand
"""

from .models import EngramAtom, RoutingResult, Track, EmotionDecayProfile
from .atom_store import EngramScopedStore, ContinuousResolutionFSM
from .atomizer import EmotionAwareAtomizer, EmotionGate, InformationRouter
from .retriever import EngramScopedRetriever
from .router import ThreePhaseRouter, EngramRouter
from .causal_dag import SparseCrossEngramDAG
from .prompt_builder import EngramAwarePromptBuilder
from .engine import EngramEngine, EngramEngineConfig
from .recall_trigger import RecallTriggerDetector

__version__ = "1.1.0"
__all__ = [
    "EngramAtom",
    "RoutingResult",
    "Track",
    "EmotionDecayProfile",
    "EngramScopedStore",
    "ContinuousResolutionFSM",
    "EmotionAwareAtomizer",
    "EmotionGate",
    "InformationRouter",
    "EngramScopedRetriever",
    "ThreePhaseRouter",
    "EngramRouter",
    "SparseCrossEngramDAG",
    "EngramAwarePromptBuilder",
    "EngramEngine",
    "EngramEngineConfig",
    "RecallTriggerDetector",
]
