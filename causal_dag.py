import uuid
import logging
from typing import List, Dict

from models import EngramAtom

logger = logging.getLogger("mem-Engram.causal_dag")


class SparseCrossEngramDAG:
    def __init__(self, atom_store=None):
        self.atom_store = atom_store
        self._edges: Dict[str, List[str]] = {}

    def try_add_cross_engram_edge(self, parent_id: str, child_id: str):
        if parent_id not in self._edges:
            self._edges[parent_id] = []
        if child_id not in self._edges[parent_id]:
            self._edges[parent_id].append(child_id)
            logger.debug(f"Added cross-engram edge: {parent_id} -> {child_id}")

    def get_children(self, atom_id: str) -> List[str]:
        return self._edges.get(atom_id, [])

    def get_parents(self, atom_id: str) -> List[str]:
        parents = []
        for pid, children in self._edges.items():
            if atom_id in children:
                parents.append(pid)
        return parents
