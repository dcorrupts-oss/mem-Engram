"""
mem-Engram Baseline Adapter
"""

import json
import os
import re
import requests
import sys

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLMEM_DIR = os.path.dirname(BENCH_DIR)
sys.path.insert(0, SKILLMEM_DIR)

from engine import EngramEngine, EngramEngineConfig
from benchmark import BaselineAdapter, call_llm

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:latest"
TIMEOUT = 120


class EngramBaseline(BaselineAdapter):
    def __init__(self):
        self._name = "mem-engram"
        self._preprocess_tokens = 0
        self._reset_engine()
        self.chat_history = []
        self.token_log = []
        self.meta_log = []

    def _reset_engine(self):
        baseline_ref = self
        def tracked_extract(raw_input: str):
            prompt = f"""从以下文本中提取结构化事实，每条包含key和value。可用key: CHARACTER_NAME, CHARACTER_TRAIT, CHARACTER_GOAL, CHARACTER_RELATION, WORLD_RULE, WORLD_LOCATION, WORLD_FACTION, WORLD_HISTORY, PLOT_EVENT, PLOT_CONFLICT, PLOT_RESOLUTION, USER_PREF, USER_FACT, EVENT, CODE_SPEC, CODE_PATTERN, TASK_CONTEXT, DATA_POINT, HR_POLICY, EMOTION_EVENT

key使用规则:
- CODE_SPEC: 代码规范/命名规则/文件结构要求
- CODE_PATTERN: 代码模式/组件写法/API调用方式
- DATA_POINT: 数据/数字/财务指标/统计信息
- HR_POLICY: 人事政策/邮件模板/员工管理
- EMOTION_EVENT: 情感事件/情绪状态/敏感信息
- TASK_CONTEXT: 任务背景/项目信息/上下文
- 其他key按原有规则使用

文本: {raw_input}

只输出JSON。"""
            resp, total, pt, ct = call_llm([{"role": "user", "content": prompt}], max_tokens=256)
            baseline_ref._preprocess_tokens += total
            try:
                match = re.search(r'\{.*\}', resp, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    return data.get("atoms", [])
            except:
                pass
            return []

        config = EngramEngineConfig(llm_extract_fn=tracked_extract)
        self.engine = EngramEngine(config=config)
        self.engine.register_agent("bench_agent")

    @property
    def name(self):
        return self._name

    def process(self, user_input, round_num):
        result = self.engine.process(user_input, "bench_agent")
        active_engrams = result["routing"]["active_engrams"]
        emotion = result["routing"]["emotion"]
        prompt_context = result["prompt"]

        system = f"""你是一个智能AI助手。

【记忆上下文】
{prompt_context if prompt_context else "暂无记忆"}"""

        messages = [{"role": "system", "content": system}]
        recent = self.chat_history[-6:]
        for msg in recent:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        resp, total, pt, ct = call_llm(messages)
        self.token_log.append({"round": round_num, "total": total, "prompt": pt, "completion": ct})
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": resp})

        self.meta_log.append({
            "round": round_num,
            "emotion": emotion,
            "activated": active_engrams,
            "atoms_created": result.get("atoms_created", 0),
            "atoms_retrieved": result.get("atoms_retrieved", 0),
        })
        return resp

    def reset(self):
        self._reset_engine()
        self.chat_history = []
        self.token_log = []
        self.meta_log = []
        self._preprocess_tokens = 0

    def get_total_tokens(self):
        return sum(t["total"] for t in self.token_log) + self._preprocess_tokens

    def get_metadata(self):
        return {"meta_log": self.meta_log, "token_log": self.token_log, "preprocess_tokens": self._preprocess_tokens}
