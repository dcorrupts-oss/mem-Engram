import logging
from typing import List, Dict, Set

from models import EngramAtom, Track, RoutingResult
from retriever import ScoredAtom

logger = logging.getLogger("mem-Engram.prompt_builder")

MEMORY_CITATION_RULE = "【记忆引用规则】引用记忆时请使用原始关键词。"


class EngramAwarePromptBuilder:
    def __init__(self, max_chars: int = 2000):
        self.max_chars = max_chars

    def build(self, routing_result: RoutingResult) -> str:
        active_engrams = routing_result.active_skills
        retrieved = routing_result.retrieved_atoms
        emotion = routing_result.emotion

        all_relevant_engrams: Set[str] = set(active_engrams)
        for scored_atom in retrieved:
            atom = scored_atom.atom if hasattr(scored_atom, "atom") else scored_atom
            all_relevant_engrams.add(atom.primary_engram)
        all_relevant_engrams.discard("general")
        if "general" not in all_relevant_engrams:
            all_relevant_engrams.add("general")

        engram_groups = self._group_by_engram(retrieved, active_engrams)

        need_citation_rule = False
        for scored_atom in retrieved:
            atom = scored_atom.atom if hasattr(scored_atom, "atom") else scored_atom
            if atom.track == Track.EPISODIC:
                need_citation_rule = True
                break
            if "EMOTION_EVENT" in atom.key:
                need_citation_rule = True
                break

        sections = []
        for engram in active_engrams:
            atoms_in_group = engram_groups.get(engram, [])
            if not atoms_in_group:
                continue
            facts = []
            for scored_atom in atoms_in_group[:5]:
                atom = scored_atom.atom if hasattr(scored_atom, "atom") else scored_atom
                facts.append(f"- {atom.key}: {atom.value}")
            if facts:
                sections.append(f"【{engram}】\n" + "\n".join(facts))

        if "general" in engram_groups and engram_groups["general"]:
            facts = []
            for scored_atom in engram_groups["general"][:3]:
                atom = scored_atom.atom if hasattr(scored_atom, "atom") else scored_atom
                facts.append(f"- {atom.key}: {atom.value}")
            if facts:
                sections.append(f"【通用】\n" + "\n".join(facts))

        if not sections:
            return ""

        header = self._build_header(emotion, active_engrams)

        parts = [header]
        if need_citation_rule:
            parts.append(MEMORY_CITATION_RULE)
        body = "\n\n".join(sections)

        full_text = "\n\n".join(parts) + "\n\n" + body

        if len(full_text) > self.max_chars:
            full_text = self._truncate(full_text)

        return full_text

    def _group_by_engram(self, retrieved: List, active_engrams: List[str]) -> Dict[str, List]:
        groups: Dict[str, List] = {e: [] for e in active_engrams}
        groups.setdefault("general", [])
        for scored_atom in retrieved:
            atom = scored_atom.atom if hasattr(scored_atom, "atom") else scored_atom
            if atom.primary_engram in groups:
                groups[atom.primary_engram].append(scored_atom)
            else:
                groups["general"].append(scored_atom)
        return groups

    def _build_header(self, emotion: str, active_engrams: List[str]) -> str:
        parts = []
        if emotion and emotion != "NEUTRAL":
            parts.append(f"[情绪状态: {emotion}]")
        if active_engrams:
            parts.append(f"[激活领域: {', '.join(active_engrams)}]")
        return " ".join(parts) if parts else ""

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text
        return text[:self.max_chars - 50] + "\n\n...(已截断)"
