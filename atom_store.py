import math
import time
import threading
import logging
from typing import List, Dict, Optional
from collections import defaultdict

from models import EngramAtom, Track

logger = logging.getLogger("mem-Engram.atom_store")


class ContinuousResolutionFSM:
    @staticmethod
    def compute_resolution(atom: EngramAtom, current_step: int = None) -> float:
        if current_step is None:
            current_step = atom.created_step
        steps_elapsed = max(0, current_step - atom.created_step)
        base_resolution = atom.write_strength * math.exp(-atom.decay_lambda * steps_elapsed)
        access_boost = 1 + 0.15 * atom.access_count
        return base_resolution * access_boost

    @staticmethod
    def on_access(atom: EngramAtom, current_step: int = None):
        atom.access_count += 1
        if current_step is not None:
            atom.last_access_step = current_step


class EngramScopedStore:
    def __init__(self):
        self._atoms: Dict[str, EngramAtom] = {}
        self._agent_index: Dict[str, List[str]] = defaultdict(list)
        self._engram_index_internal: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()

    def put(self, atom: EngramAtom):
        with self._lock:
            self._atoms[atom.atom_id] = atom
            self._agent_index[atom.key.split(":")[0] if ":" in atom.key else "default"].append(atom.atom_id)
            self._engram_index_internal[atom.primary_engram].append(atom.atom_id)
            for sec in atom.secondary_engrams:
                self._engram_index_internal[sec].append(atom.atom_id)

    def get(self, atom_id: str) -> Optional[EngramAtom]:
        return self._atoms.get(atom_id)

    def find_by_agent(self, agent_id: str) -> List[EngramAtom]:
        atom_ids = self._agent_index.get(agent_id, [])
        return [self._atoms[aid] for aid in atom_ids if aid in self._atoms]

    def find_by_engram(self, engram: str) -> List[EngramAtom]:
        atom_ids = self._engram_index_internal.get(engram, [])
        return [self._atoms[aid] for aid in atom_ids if aid in self._atoms]

    def all_atoms(self) -> List[EngramAtom]:
        return list(self._atoms.values())

    @property
    def _engram_index(self):
        return self._engram_index_internal
