import uuid
import time
import threading
import logging
from typing import List, Dict, Callable, Optional

from models import EngramAtom, RoutingResult, Track
from atom_store import EngramScopedStore, ContinuousResolutionFSM
from atomizer import EmotionAwareAtomizer, EmotionGate, InformationRouter
from retriever import EngramScopedRetriever
from router import ThreePhaseRouter, EngramRouter
from causal_dag import SparseCrossEngramDAG
from prompt_builder import EngramAwarePromptBuilder

logger = logging.getLogger("mem-Engram.engine")


class EngramEngineConfig:
    def __init__(
        self,
        embed_fn: Optional[Callable] = None,
        llm_extract_fn: Optional[Callable] = None,
        llm_client: object = None,
        max_atoms: int = 1000,
        engram_keywords: Dict[str, List[str]] = None,
    ):
        self.embed_fn = embed_fn
        self.llm_extract_fn = llm_extract_fn
        self.llm_client = llm_client
        self.max_atoms = max_atoms
        self.engram_keywords = engram_keywords


class EngramEngine:
    def __init__(self, config: EngramEngineConfig = None, **kwargs):
        if config is None:
            config = EngramEngineConfig(**kwargs)
        self._cfg = config

        self.atom_store = EngramScopedStore()
        self.emotion_gate = EmotionGate()
        self.info_router = InformationRouter()
        self.atomizer = EmotionAwareAtomizer(
            emotion_gate=self.emotion_gate,
            info_router=self.info_router,
            llm_extract_fn=config.llm_extract_fn,
        )
        self.retriever = EngramScopedRetriever(
            atom_store=self.atom_store,
            embed_fn=config.embed_fn,
        )
        self.engram_router = EngramRouter(engram_keywords=config.engram_keywords)
        self.three_phase_router = ThreePhaseRouter(
            engram_router=self.engram_router,
            emotion_gate=self.emotion_gate,
            atom_store=self.atom_store,
            retriever=self.retriever,
        )
        self.causal_dag = SparseCrossEngramDAG(atom_store=self.atom_store)
        self.prompt_builder = EngramAwarePromptBuilder()

        self.agents: Dict[str, dict] = {}
        self._ingest_lock = threading.RLock()
        self._step_counter: Dict[str, int] = {}

    def register_agent(self, agent_id: str, name: str = ""):
        self.agents[agent_id] = {"name": name, "agent_id": agent_id}
        self._step_counter[agent_id] = 0
        logger.info(f"Agent registered: {agent_id}")

    def process(self, user_input: str, agent_id: str) -> dict:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not registered")

        self._step_counter[agent_id] = self._step_counter.get(agent_id, 0) + 1
        current_step = self._step_counter[agent_id]

        routing_result = self.three_phase_router.route(
            user_input=user_input,
            agent_id=agent_id,
            current_step=current_step,
        )

        atoms = self.atomizer.extract(
            raw_input=user_input,
            agent_id=agent_id,
            current_step=current_step,
            active_engrams=routing_result.write_scope,
        )

        with self._ingest_lock:
            for atom in atoms:
                self.atom_store.put(atom)
                self.retriever.index_atom(atom)

        self._build_cross_engram_links(atoms)

        prompt = self.prompt_builder.build(routing_result)

        return {
            "routing": {
                "emotion": routing_result.emotion,
                "active_engrams": routing_result.active_skills,
                "write_scope": routing_result.write_scope,
            },
            "atoms_created": len(atoms),
            "atoms_retrieved": len(routing_result.retrieved_atoms),
            "prompt": prompt,
            "step": current_step,
        }

    def _build_cross_engram_links(self, atoms: List[EngramAtom]):
        if len(atoms) < 2:
            return
        for i in range(len(atoms)):
            for j in range(i + 1, len(atoms)):
                parent = atoms[i]
                child = atoms[j]
                if parent.primary_engram != child.primary_engram:
                    self.causal_dag.try_add_cross_engram_edge(parent.atom_id, child.atom_id)
                else:
                    parent.causal_children.append(child.atom_id)
                    child.causal_parents.append(parent.atom_id)
                    self.atom_store.update(parent)
