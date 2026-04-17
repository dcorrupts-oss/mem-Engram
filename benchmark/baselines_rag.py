import json
import os
import math
from benchmark import BaselineAdapter, call_llm


class SlidingWindowRAGBaseline(BaselineAdapter):
    def __init__(self, window_size=6):
        self._name = "sliding_window_rag"
        self.window_size = window_size
        self.chat_history = []
        self.all_facts = []
        self.token_log = []
        self.meta_log = []
        self._extract_tokens = 0
        self._fact_index = {}
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
        self._fact_index = {}
        self._doc_lengths = {}
        for idx, f in enumerate(self.all_facts):
            tokens = self._tokenize(f)
            self._doc_lengths[idx] = len(tokens)
            for term in tokens:
                if term not in self._fact_index:
                    self._fact_index[term] = []
                if idx not in self._fact_index[term]:
                    self._fact_index[term].append(idx)
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def _bm25_search(self, query, top_k=5, k1=1.5, b=0.75):
        if not self.all_facts:
            return ""
        query_terms = self._tokenize(query)
        if not query_terms:
            return ""
        N = len(self.all_facts)
        scores = {}
        for term in query_terms:
            df = len(self._fact_index.get(term, []))
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            if idf <= 0:
                continue
            for doc_idx in self._fact_index.get(term, []):
                tf = sum(1 for t in self._tokenize(self.all_facts[doc_idx]) if t == term)
                doc_len = self._doc_lengths.get(doc_idx, 1)
                norm = 1 - b + b * (doc_len / (self._avg_doc_length + 1e-8))
                score = idf * (tf * (k1 + 1)) / (tf + k1 * norm)
                scores[doc_idx] = scores.get(doc_idx, 0.0) + score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top = [self.all_facts[idx] for idx, s in ranked[:top_k] if s > 0]
        return "\n".join([f"- {f}" for f in top]) if top else ""

    def _extract_facts(self, user_input, response):
        prompt = f"""从对话中提取关键事实，每条不超过20字。
用户: {user_input}
助手: {response[:200]}
输出JSON数组: ["事实1", "事实2"]"""
        resp, total, _, _ = call_llm([{"role": "user", "content": prompt}], max_tokens=128, use_cache=False)
        self._extract_tokens += total
        try:
            import re
            match = re.search(r'\[.*\]', resp, re.DOTALL)
            if match:
                items = json.loads(match.group())
                for item in items:
                    if item and item not in self.all_facts:
                        self.all_facts.append(item)
        except:
            pass

    def _rag_search(self, query, top_k=5):
        if not self.all_facts:
            return ""
        self._build_index()
        return self._bm25_search(query, top_k)

    def process(self, user_input, round_num):
        rag_context = self._rag_search(user_input)

        system = f"""你是一个智能AI助手。

【检索到的相关事实】
{rag_context if rag_context else "暂无"}"""

        messages = [{"role": "system", "content": system}]
        window = self.chat_history[-self.window_size:]
        for msg in window:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        resp, total, pt, ct = call_llm(messages)
        self.token_log.append({"round": round_num, "total": total, "prompt": pt, "completion": ct})
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": resp})

        self._extract_facts(user_input, resp)

        self.meta_log.append({
            "round": round_num,
            "facts_count": len(self.all_facts),
            "window_used": len(window),
        })
        return resp

    def reset(self):
        self.chat_history = []
        self.all_facts = []
        self.token_log = []
        self.meta_log = []
        self._extract_tokens = 0
        self._fact_index = {}
        self._doc_lengths = {}
        self._avg_doc_length = 0

    def get_total_tokens(self):
        return sum(t["total"] for t in self.token_log) + self._extract_tokens

    def get_metadata(self):
        return {"meta_log": self.meta_log, "token_log": self.token_log}
