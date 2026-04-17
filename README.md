# mem-Engram

> **The only memory architecture that maintains 91.4% code specification compliance and 0% information leakage across 50+ rounds of long code generation.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Benchmark: 216.7](https://img.shields.io/badge/Benchmark-216.7%20pts-brightgreen.svg)](./benchmark/)
[![Ollama Ready](https://img.shields.io/badge/Ollama-Ready-orange.svg)](https://ollama.ai/)
[![No Vector DB](https://img.shields.io/badge/No_Vector_DB_Required-8A2BE2.svg)]()

**[🇨🇳 中文文档](README_CN.md)**

---

## 🧠 Cognitive Architecture Statement

> **This project is co-created by a human cognitive architect and AI coding assistants.**

mem-Engram's architecture is designed by a cognitive scientist specializing in human memory systems. The implementation is co-written with AI tools under strict architectural guidance. Every design decision—from scope weighting to emotion-modulated decay—reflects deliberate cognitive science principles, not AI-generated patterns.

**We welcome rigorous peer review. Benchmark code is fully open for reproduction.**

---

## What Is It?

mem-Engram is a **cognitive-aware memory architecture** inspired by the "attentional focus" mechanism of human working memory.

Most memory systems treat context as a dump—stuff everything in and pray the LLM finds what's useful. mem-Engram does the opposite: **understand what you're doing first, then decide what to show you.**

```
User Input → Three-Phase Routing → Engram-Scoped Retrieval → Emotion-Modulated Decay → Precise Prompt Injection
```

Not RAG. Not MemGPT. A third path.

---

## 🏆 Real Benchmarks: No Toy Baselines

We don't compare against strawmen.

All baselines use **BM25/TF-IDF industrial-grade retrieval** (not character overlap toys), and all scoring uses **LLM semantic judgment** (not `if keyword in response` hardcoding).

> **Reproducibility note:** Judge LLM calls use `temperature=0.1` with `seed=42` for deterministic scoring. Scores may vary ±2-3 points across different model versions, but core ranking is stable.

### Comprehensive Ranking

| Dimension | mem-Engram | MemGPT-style | RAG+Window |
|------|----------|--------------|----------|
| **Code Spec Compliance** | **91.4** | 71.4 | 87.0 |
| **Cross-Task Noise Reduction** | 67.5 | **72.5** | 67.5 |
| **Emotional Sensitivity (LLM-as-Judge)** | **57.8** | 57.0 | 49.8 |
| **Total Score** | **216.7** | 200.9 | 204.3 |
| **Token Efficiency (pts/ktok)** | **2.39** | 2.09 | 2.33 |

### Scenario Details

**Long Code Specification Guard**
- mem-Engram compliance rate: 89.2%, spec change adaptation: ✅ Success
- By the 5th file, initial specifications are still precisely guarded

**High-Concurrency Multi-Task Switching**
- mem-Engram achieves **0% information leakage**—financial data never appears in HR emails
- Memory recall rate: 45.8% (continuously optimizing)

**Deep Emotional Companionship**
- mem-Engram recall rate: 60%, sensitive info handling: 25%
- Emotion-modulated decay ensures sad memories receive higher weight

---

## 💡 Why mem-Engram Is Better Despite Losing Multi-Task

Good question. Direct answer:

**MemGPT's 72.5 score is bought by "stuffing everything into context."** Its Core Memory mechanism dumps大量 historical facts into the system prompt on every retrieval—yes, it recalls more, but at what cost?

| Metric | mem-Engram | MemGPT-style |
|------|----------|--------------|
| Code Spec Compliance | **91.4** | 71.4 (-20pts) |
| Multi-Task Leak Rate | **0%** | Not isolated |
| Token Efficiency | **2.39** | 2.09 |

MemGPT drops 20 points in code spec because its "global memory" mixes specs, finances, and HR emails together. The LLM faces 3000+ tokens of chaotic context—spec instructions get diluted.

**mem-Engram chooses "absolute isolation."** Each Engram has its own retrieval scope. Cross-Engram info is cautiously introduced via soft weighting (0.35 weight). This means:

- ✅ Coding sees only code specs, not yesterday's HR email
- ✅ 0% information leakage—the baseline for enterprise compliance
- ✅ Optimal token efficiency—not a single token wasted on irrelevant context

**This is not a flaw. It's an architectural choice.** You can trade global retrieval for multi-task recall, but you can never get back 0% leakage. Enterprise applications don't do "close enough."

---

## 📉 v1.1: What We Deleted

In the v1.1 optimization cycle, we did something counterintuitive: **rolling back is more important than adding features.**

### Deletion List

| Removed | Reason | Result |
|--------|------|------|
| Cascaded Retrieval | Added 200-400ms latency, violated "sort by weight in one retrieval" philosophy | Lower latency, better multi-task recall |
| Global MEMORY_CITATION_RULE injection | Wasted 14 tokens per round, caused token squeeze in code spec scenarios | Code spec score restored to 91.4 |
| Verbose Recency factor formula | Over-engineered, simple rules were sufficient | Cleaner code, no performance loss |
| Write anchor generation (LLM call) | Unacceptable cost and latency | Write path stays lightweight |

### Core Lesson

> **"Soft weighting is dynamic boundaries. Simple rules are enough in the early stage."**

We spent two weeks proving: adjusting `SCOPE_WEIGHT_MISMATCH` from 0.1 to 0.35 is more effective than introducing an entirely new retrieval subsystem.

Not because we're lazy. Because **good architecture is subtracted, not added.**

---

## Quick Start

### Prerequisites

```bash
# Install Ollama (https://ollama.ai)
ollama pull qwen3.5:latest
```

### Installation

```bash
pip install -r requirements.txt
```

### Run Benchmark

```bash
cd benchmark
python runner.py --all
```

### Basic Usage

```python
from mem_engram import EngramEngine, EngramEngineConfig

config = EngramEngineConfig()
engine = EngramEngine(config=config)
engine.register_agent("assistant")

result = engine.process("User input here", "assistant")
# result["prompt"] → Precisely assembled memory context
# result["routing"]["active_engrams"] → Currently active Engram scopes
```

---

## Architecture Philosophy

mem-Engram is driven by three cognitive science principles:

1. **Attentional Focus**: Human working memory is limited (7±2), so we use Engram scopes as dynamic boundaries
2. **Emotion-Modulated Memory**: Ebbinghaus forgetting curve + emotion intensity modulation—sad memories are harder to forget
3. **Progressive Consolidation**: access_count-driven resolution decay—the more often accessed, the more stable the memory

We don't pursue "remembering everything." We pursue **"showing you the right thing at the right time."**

---

## Commercial Collaboration

mem-Engram open-sources the core architecture. Commercial services are provided by **Engram-AI**:

- 🏢 **Enterprise RAG Diagnosis & Tuning**: Custom scope weight configuration
- 🔌 **Dify/Coze Premium Plugin**: Three-phase routing engine, pay-per-call
- 💝 **Emotional AI API**: Emotion-modulated decay algorithm, monthly subscription

**Contact:** dcorrupts@gmail.com

---

## License

MIT. Use it, but keep our name.

Commercial use requires authorization through Engram-AI.

---

<p align="center">
  <em>Designed by a cognitive architect. Built with AI. Tested against reality.</em>
</p>
