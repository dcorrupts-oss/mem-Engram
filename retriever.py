import math
import os
import re
import logging
from typing import List, Dict, Optional, Tuple

from models import EngramAtom, Track
from atom_store import EngramScopedStore, ContinuousResolutionFSM

logger = logging.getLogger("mem-Engram.retriever")

SCOPE_WEIGHT_PRIMARY = 1.0
SCOPE_WEIGHT_SECONDARY = 0.7
SCOPE_WEIGHT_GENERAL = 0.5
SCOPE_WEIGHT_MISMATCH = 0.35

BACKTRACK_KEYWORDS = [
    "回到", "刚才", "之前", "回忆", "继续说", "接着说",
    "回到刚才", "回到之前", "继续刚才", "接着刚才",
    "back to", "go back", "continue", "earlier", "previous",
    "再说", "展开", "详细说", "那个点", "那个事",
]

RECALL_TRIGGER_PATTERNS = [
    r"你还记得",
    r"之前.*说过",
    r"上次.*提到",
    r"帮我回忆",
    r"回忆一下",
    r"之前.*讲",
    r"刚才.*说",
    r"do you remember",
    r"remember.*when",
    r"之前.*聊",
    r"之前.*提",
]


def _detect_backtrack(query: str) -> bool:
    query_lower = query.lower()
    for kw in BACKTRACK_KEYWORDS:
        if kw in query_lower:
            return True
    return False


class RecallTriggerDetector:
    def __init__(self, patterns: List[str] = None):
        self.patterns = patterns or RECALL_TRIGGER_PATTERNS

    def detect(self, query: str) -> bool:
        for pattern in self.patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False


class EngramScopedRetriever:
    def __init__(
        self,
        atom_store: EngramScopedStore = None,
        embed_fn: callable = None,
    ):
        self.atom_store = atom_store
        self.embed_fn = embed_fn
        self.recall_detector = RecallTriggerDetector()

    def index_atom(self, atom: EngramAtom):
        pass

    def retrieve_with_scope(
        self,
        query: str,
        agent_id: str,
        candidate_scopes: List[str],
        top_k: int = 15,
        current_step: int = None,
    ) -> List:
        all_atoms = self.atom_store.find_by_agent(agent_id)
        if not all_atoms:
            return []

        if self.recall_detector.detect(query):
            return self._recall_retrieve(query, agent_id, top_k, current_step)

        is_backtrack = _detect_backtrack(query)
        if is_backtrack:
            candidate_scopes = list(self.atom_store._engram_index.keys())

        initial_k = 25
        dense_results = self._dense_search(query, all_atoms, initial_k * 3)
        sparse_results = self._sparse_search(query, all_atoms, initial_k * 3)
        fused = self._reciprocal_rank_fusion(dense_results, sparse_results)

        scored = []
        for atom_id, base_score in fused:
            atom = self.atom_store.get(atom_id)
            if not atom:
                continue
            scope_weight = self._compute_scope_weight(atom, candidate_scopes)
            resolution = ContinuousResolutionFSM.compute_resolution(atom, current_step=current_step)
            context_decay = self._context_pressure_decay(atom, current_step or 0)
            final_score = base_score * scope_weight * resolution * context_decay
            scored.append(ScoredAtom(atom=atom, score=final_score))

        scored.sort(key=lambda x: x.score, reverse=True)

        top_candidates = scored[:top_k]
        primary_count = sum(
            1 for sa in top_candidates
            if sa.atom.primary_engram in candidate_scopes
            or any(s in candidate_scopes for s in sa.atom.secondary_engrams)
        )
        if primary_count < top_k * 0.5 and len(scored) > top_k:
            rescored = []
            for atom_id, base_score in fused:
                atom = self.atom_store.get(atom_id)
                if not atom:
                    continue
                scope_weight = self._compute_scope_weight_cascade(atom, candidate_scopes)
                resolution = ContinuousResolutionFSM.compute_resolution(atom, current_step=current_step)
                context_decay = self._context_pressure_decay(atom, current_step or 0)
                final_score = base_score * scope_weight * resolution * context_decay
                rescored.append(ScoredAtom(atom=atom, score=final_score))
            rescored.sort(key=lambda x: x.score, reverse=True)
            scored = rescored

        debug_enabled = os.environ.get('MEM_ENGRAM_DEBUG_RECALL') == 'true'
        if debug_enabled:
            logger.info(f"Retrieval debug: query='{query[:50]}', scopes={candidate_scopes}")
            for sa in scored[:5]:
                logger.info(f"  atom={sa.atom.key}, score={sa.score:.4f}, engram={sa.atom.primary_engram}")

        for sa in scored[:top_k]:
            ContinuousResolutionFSM.on_access(sa.atom)
        return scored[:top_k]

    def _recall_retrieve(self, query: str, agent_id: str, top_k: int, current_step: int):
        all_atoms = self.atom_store.find_by_agent(agent_id)
        if not all_atoms:
            return []
        scored = []
        for atom in all_atoms:
            resolution = ContinuousResolutionFSM.compute_resolution(atom, current_step=current_step)
            recency = math.exp(-0.05 * max(0, (current_step or 0) - atom.created_step))
            final_score = resolution * (0.7 + 0.3 * recency)
            scored.append(ScoredAtom(atom=atom, score=final_score))
        scored.sort(key=lambda x: x.score, reverse=True)
        for sa in scored[:top_k]:
            ContinuousResolutionFSM.on_access(sa.atom)
        return scored[:top_k]

    def _dense_search(self, query: str, atoms: List[EngramAtom], top_k: int) -> List[Tuple[str, float]]:
        if self.embed_fn:
            try:
                query_vec = self.embed_fn(query)
                scored = []
                for atom in atoms:
                    atom_vec = self.embed_fn(atom.value)
                    sim = self._cosine_sim(query_vec, atom_vec)
                    scored.append((atom.atom_id, sim))
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[:top_k]
            except:
                pass
        return self._keyword_search(query, atoms, top_k)

    def _sparse_search(self, query: str, atoms: List[EngramAtom], top_k: int) -> List[Tuple[str, float]]:
        return self._keyword_search(query, atoms, top_k)

    def _keyword_search(self, query: str, atoms: List[EngramAtom], top_k: int) -> List[Tuple[str, float]]:
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        scored = []
        for atom in atoms:
            value_lower = atom.value.lower()
            overlap = sum(1 for t in query_terms if t in value_lower)
            key_match = 2.0 if any(t in atom.key.lower() for t in query_terms) else 0
            score = overlap + key_match
            if score > 0:
                scored.append((atom.atom_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _reciprocal_rank_fusion(self, dense: List[Tuple[str, float]], sparse: List[Tuple[str, float]], k: int = 60) -> Dict[str, float]:
        fused = {}
        for rank, (atom_id, _) in enumerate(dense):
            fused[atom_id] = fused.get(atom_id, 0) + 1 / (k + rank + 1)
        for rank, (atom_id, _) in enumerate(sparse):
            fused[atom_id] = fused.get(atom_id, 0) + 1 / (k + rank + 1)
        return sorted(fused.items(), key=lambda x: x[1], reverse=True)

    def _compute_scope_weight(self, atom: EngramAtom, candidate_scopes: List[str]) -> float:
        if not candidate_scopes:
            return SCOPE_WEIGHT_GENERAL
        if atom.primary_engram in candidate_scopes:
            return SCOPE_WEIGHT_PRIMARY
        for sec in atom.secondary_engrams:
            if sec in candidate_scopes:
                return SCOPE_WEIGHT_SECONDARY
        if "general" in candidate_scopes and atom.primary_engram == "general":
            return SCOPE_WEIGHT_GENERAL
        return SCOPE_WEIGHT_MISMATCH

    def _compute_scope_weight_cascade(self, atom: EngramAtom, candidate_scopes: List[str]) -> float:
        if not candidate_scopes:
            return SCOPE_WEIGHT_GENERAL
        if atom.primary_engram in candidate_scopes:
            return SCOPE_WEIGHT_PRIMARY
        for sec in atom.secondary_engrams:
            if sec in candidate_scopes:
                return SCOPE_WEIGHT_SECONDARY
        if "general" in candidate_scopes and atom.primary_engram == "general":
            return SCOPE_WEIGHT_GENERAL
        return SCOPE_WEIGHT_MISMATCH * 1.8

    def _context_pressure_decay(self, atom: EngramAtom, current_step: int) -> float:
        steps_back = max(0, current_step - atom.created_step)
        return math.exp(-0.02 * steps_back)

    def _cosine_sim(self, vec1, vec2):
        if not vec1 or not vec2:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


class ScoredAtom:
    def __init__(self, atom: EngramAtom, score: float):
        self.atom = atom
        self.score = score
