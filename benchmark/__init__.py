"""
mem-Engram Benchmark Framework
Engram-AI Commercial Brand
"""

import json
import os
import time
import requests
from typing import List, Dict, Callable

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BENCHMARK_DIR, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:latest"
TIMEOUT = 120


class BaselineAdapter:
    @property
    def name(self) -> str:
        raise NotImplementedError

    def process(self, user_input: str, round_num: int) -> str:
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def get_total_tokens(self) -> int:
        return 0

    def get_metadata(self) -> dict:
        return {}


def call_llm(messages: list, max_tokens: int = 512, use_cache: bool = True, temperature: float = 0.7, seed: int = None) -> tuple:
    cache_key = None
    if use_cache:
        import hashlib
        content = json.dumps(messages, sort_keys=True) + str(max_tokens) + str(temperature) + str(seed)
        cache_key = hashlib.md5(content.encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                cached = json.load(f)
            return cached["response"], cached["total_tokens"], cached["prompt_tokens"], cached["completion_tokens"]

    options = {
        "num_predict": max_tokens,
        "temperature": temperature,
    }
    if seed is not None:
        options["seed"] = seed

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": options,
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        response = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        total_tokens = prompt_tokens + completion_tokens

        if use_cache and cache_key:
            with open(cache_path, "w") as f:
                json.dump({
                    "response": response,
                    "total_tokens": total_tokens,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }, f)

        return response, total_tokens, prompt_tokens, completion_tokens
    except Exception as e:
        print(f"LLM call failed: {e}")
        return "", 0, 0, 0
