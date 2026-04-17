import json
import os
import re
import math
import requests
from benchmark import BaselineAdapter, call_llm

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:latest"
TIMEOUT = 120


class MemGPTStyleBaseline(BaselineAdapter):
    def __init__(self):
        self._name = "memgpt_style"
        self.core_memory = []
        self.archival_memory = []
        self.chat_history = []
        self.token_log = []
        self.meta_log = []
        self._extract_tokens = 0
        self._archival_index = {}
        self._doc_lengths = {}
        self._avg_doc_length = 0

    @property
    def name(self):
        return self._name

    def _tokenize(self, text: str):
        if not isinstance(text, str):
            return []
        tokens = []
        cleaned = text.replace("，", " ").replace("。", " ").replace("、", " ").replace("：", " ")
        for word in cleaned.split():
            word = word.strip().lower()
            if not word:
                continue
            tokens.append(word)
            if len(word) >= 2:
                for i in range(len(word) - 1):
                    tokens.append(word[i : i + 2])
        return tokens

    def _build_index(self):
        self._archival_index = {}
        self._doc_lengths = {}
        for idx, m in enumerate(self.archival_memory):
            tokens = self._tokenize(m)
            self._doc_lengths[idx] = len(tokens)
            for term in tokens:
                if term not in self._archival_index:
                    self._archival_index[term] = []
                if idx not in self._archival_index[term]:
                    self._archival_index[term].append(idx)
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def _bm25_search(self, query, top_k=5, k1=1.5, b=0.75):
        if not self.archival_memory:
            return ""
        query_terms = self._tokenize(query)
        if not query_terms:
            return ""
        N = len(self.archival_memory)
        scores = {}
        for term in query_terms:
            df = len(self._archival_index.get(term, []))
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            if idf <= 0:
                continue
            for doc_idx in self._archival_index.get(term, []):
                tf = sum(1 for t in self._tokenize(self.archival_memory[doc_idx]) if t == term)
                doc_len = self._doc_lengths.get(doc_idx, 1)
                norm = 1 - b + b * (doc_len / (self._avg_doc_length + 1e-8))
                score = idf * (tf * (k1 + 1)) / (tf + k1 * norm)
                scores[doc_idx] = scores.get(doc_idx, 0.0) + score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top = [self.archival_memory[idx] for idx, s in ranked[:top_k] if s > 0]
        return "\n".join([f"- {m}" for m in top]) if top else ""

    def _extract_to_core(self, user_input, response):
        prompt = f"""从对话中提取关键事实到Core Memory（有限容量，只保留最重要的）。每条不超过30字。
用户: {user_input}
助手: {response[:300]}
输出JSON: {{"core": ["事实1", "事实2"]}}"""
        resp, total, _, _ = call_llm([{"role": "user", "content": prompt}], max_tokens=256, use_cache=False)
        self._extract_tokens += total
        try:
            match = re.search(r'\{.*\}', resp, re.DOTALL)
            if match:
                data = json.loads(match.group())
                for item in data.get("core", []):
                    if item and item not in self.core_memory:
                        self.core_memory.append(item)
                        if len(self.core_memory) > 10:
                            self.core_memory.pop(0)
        except:
            pass

    def _extract_to_archival(self, user_input, response):
        prompt = f"""从对话中提取所有可能有用的事实到Archival Memory。每条不超过30字。
用户: {user_input}
助手: {response[:300]}
输出JSON: {{"archival": ["事实1", "事实2"]}}"""
        resp, total, _, _ = call_llm([{"role": "user", "content": prompt}], max_tokens=256, use_cache=False)
        self._extract_tokens += total
        try:
            match = re.search(r'\{.*\}', resp, re.DOTALL)
            if match:
                data = json.loads(match.group())
                for item in data.get("archival", []):
                    if item and item not in self.archival_memory:
                        self.archival_memory.append(item)
        except:
            pass

    def _search_archival(self, query, top_k=5):
        if not self.archival_memory:
            return ""
        self._build_index()
        return self._bm25_search(query, top_k)

    def process(self, user_input, round_num):
        core_text = "\n".join([f"- {m}" for m in self.core_memory])
        archival_text = self._search_archival(user_input)

        system = f"""你是一个智能AI助手。

【Core Memory（核心记忆，始终可见）】
{core_text if core_text else "暂无"}

【Archival Memory（检索到的归档记忆）】
{archival_text if archival_text else "暂无"}"""

        messages = [{"role": "system", "content": system}]
        recent = self.chat_history[-6:]
        for msg in recent:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        resp, total, pt, ct = call_llm(messages)
        self.token_log.append({"round": round_num, "total": total, "prompt": pt, "completion": ct})
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": resp})

        self._extract_to_core(user_input, resp)
        self._extract_to_archival(user_input, resp)

        self.meta_log.append({
            "round": round_num,
            "core_size": len(self.core_memory),
            "archival_size": len(self.archival_memory),
        })
        return resp

    def reset(self):
        self.core_memory = []
        self.archival_memory = []
        self.chat_history = []
        self.token_log = []
        self.meta_log = []
        self._extract_tokens = 0
        self._archival_index = {}
        self._doc_lengths = {}
        self._avg_doc_length = 0

    def get_total_tokens(self):
        return sum(t["total"] for t in self.token_log) + self._extract_tokens

    def get_metadata(self):
        return {"meta_log": self.meta_log, "token_log": self.token_log}
