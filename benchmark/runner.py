"""
mem-Engram Benchmark Runner
Engram-AI Commercial Brand
"""

import json
import os
import sys
import time
from datetime import datetime

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BENCH_DIR)
sys.path.insert(0, os.path.dirname(BENCH_DIR))

from benchmark import BaselineAdapter, call_llm

RESULTS_DIR = os.path.join(BENCH_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_scenario(baseline: BaselineAdapter, scenario_module) -> list:
    baseline.reset()
    round_results = []
    rounds = scenario_module.get_rounds()
    for i, round_data in enumerate(rounds):
        user_input = round_data["input"]
        resp = baseline.process(user_input, i + 1)
        round_result = {
            "round": i + 1,
            "input": user_input,
            "response": resp,
            "expected": round_data.get("expected", {}),
        }
        if "emotion" in round_data:
            round_result["emotion"] = round_data["emotion"]
        if "check_recall" in round_data:
            round_result["check_recall"] = round_data["check_recall"]
        if "check_no_leak" in round_data:
            round_result["check_no_leak"] = round_data["check_no_leak"]
        if "check_spec" in round_data:
            round_result["check_spec"] = round_data["check_spec"]
        round_results.append(round_result)
    return round_results


def run_benchmark(scenario_names: list, baseline_names: list) -> dict:
    all_results = {}
    for scenario_name in scenario_names:
        print(f"\n{'='*60}")
        print(f"  场景: {_get_scenario_title(scenario_name)}")
        print(f"{'='*60}")

        scenario_module = _load_scenario(scenario_name)
        judge_fn = _load_judge(scenario_name)

        scenario_results = {"scenario": _get_scenario_title(scenario_name), "baselines": {}}

        for baseline_name in baseline_names:
            baseline = _load_baseline(baseline_name)
            print(f"\n  基线: {baseline_name}...", end=" ", flush=True)

            round_results = run_scenario(baseline, scenario_module)
            judgment = judge_fn(round_results)
            total_tokens = baseline.get_total_tokens()
            token_efficiency = round(judgment["score"] / (total_tokens / 1000), 2) if total_tokens > 0 else 0

            scenario_results["baselines"][baseline_name] = {
                "score": judgment["score"],
                "total_tokens": total_tokens,
                "token_efficiency": token_efficiency,
                "judgment": judgment,
            }
            print(f"得分: {judgment['score']} | Token: {total_tokens}")

        all_results[scenario_name] = scenario_results

    return all_results


def _get_scenario_title(name: str) -> str:
    titles = {
        "code_spec": "长代码工程规范守护",
        "multi_task": "高并发多任务切换",
        "emotion": "深度情感陪伴",
    }
    return titles.get(name, name)


def _load_scenario(name: str):
    if name == "code_spec":
        from benchmark import scenario_code_spec
        return scenario_code_spec
    elif name == "multi_task":
        from benchmark import scenario_multi_task
        return scenario_multi_task
    elif name == "emotion":
        from benchmark import scenario_emotion
        return scenario_emotion
    raise ValueError(f"Unknown scenario: {name}")


def _load_judge(name: str):
    if name == "code_spec":
        from benchmark.scenario_code_spec import judge_code_spec
        return judge_code_spec
    elif name == "multi_task":
        from benchmark.scenario_multi_task import judge_multi_task
        return judge_multi_task
    elif name == "emotion":
        from benchmark.scenario_emotion import judge_emotion_companion
        return judge_emotion_companion
    raise ValueError(f"Unknown judge: {name}")


def _load_baseline(name: str) -> BaselineAdapter:
    if name == "skillmem":
        from benchmark.baselines_skillmem import EngramBaseline
        return EngramBaseline()
    elif name == "memgpt_style":
        from benchmark.baselines_memgpt import MemGPTStyleBaseline
        return MemGPTStyleBaseline()
    elif name == "sliding_window_rag":
        from benchmark.baselines_rag import SlidingWindowRAGBaseline
        return SlidingWindowRAGBaseline()
    raise ValueError(f"Unknown baseline: {name}")


def generate_report(results: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR, f"report_{timestamp}.txt")
    json_path = os.path.join(RESULTS_DIR, f"benchmark_{timestamp}.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("=" * 70)
    lines.append("  mem-Engram 行业对标 Benchmark 报告")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    for scenario_name, scenario_data in results.items():
        lines.append(f"\n{'='*60}")
        lines.append(f"  场景: {scenario_data['scenario']}")
        lines.append(f"{'='*60}")
        lines.append(f"{'基线':<30}{'得分':<8}{'Token':<10}{'效率(分/ktok)':<15}")
        lines.append("-" * 60)

        baselines = scenario_data["baselines"]
        sorted_baselines = sorted(baselines.items(), key=lambda x: x[1]["score"], reverse=True)
        for bname, bdata in sorted_baselines:
            lines.append(f"{bname:<30}{bdata['score']:<8}{bdata['total_tokens']:<10}{bdata['token_efficiency']:<15}")

        judgment = sorted_baselines[0][1]["judgment"]
        if "compliance_rate" in judgment:
            lines.append(f"\n  规范遵守率: {judgment['compliance_rate']*100:.1f}%")
        if "spec_change_ok" in judgment:
            lines.append(f"  规范变更适应: {'成功' if judgment['spec_change_ok'] else '失败'}")
        if "recall_rate" in judgment:
            lines.append(f"\n  记忆召回率: {judgment['recall_rate']*100:.1f}%")
        if "sensitivity_rate" in judgment:
            lines.append(f"  敏感信息处理: {judgment['sensitivity_rate']*100:.1f}%")

    lines.append(f"\n{'='*70}")
    lines.append("  综合对比")
    lines.append(f"{'='*70}")
    lines.append(f"{'基线':<30}{'总分':<10}{'均分':<10}{'总Token':<10}")
    lines.append("-" * 60)

    totals = {}
    for scenario_name, scenario_data in results.items():
        for bname, bdata in scenario_data["baselines"].items():
            if bname not in totals:
                totals[bname] = {"total_score": 0, "count": 0, "total_tokens": 0}
            totals[bname]["total_score"] += bdata["score"]
            totals[bname]["count"] += 1
            totals[bname]["total_tokens"] += bdata["total_tokens"]

    sorted_totals = sorted(totals.items(), key=lambda x: x[1]["total_score"], reverse=True)
    for bname, tdata in sorted_totals:
        avg = round(tdata["total_score"] / tdata["count"], 1)
        lines.append(f"{bname:<30}{tdata['total_score']:<10}{avg:<10}{tdata['total_tokens']:<10}")

    lines.append(f"\n{'='*70}")
    lines.append("  行业对标矩阵")
    lines.append(f"{'='*70}")
    lines.append(f"\n{'维度':<25}{'mem-Engram':<15}{'MemGPT-style':<15}{'RAG+窗口':<15}")
    lines.append("-" * 70)

    scenario_keys = list(results.keys())
    for i, sk in enumerate(scenario_keys):
        scenario_data = results[sk]
        baselines = scenario_data["baselines"]
        engram_score = baselines.get("skillmem", {}).get("score", 0)
        memgpt_score = baselines.get("memgpt_style", {}).get("score", 0)
        rag_score = baselines.get("sliding_window_rag", {}).get("score", 0)
        title = _get_scenario_title(sk)
        lines.append(f"{title:<25}{engram_score:<15}{memgpt_score:<15}{rag_score:<15}")

    report_text = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n{report_text}")
    print(f"\n报告已保存: {report_path}")
    print(f"JSON 数据: {json_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="mem-Engram Benchmark Runner")
    parser.add_argument("--scenario", nargs="+", default=None, help="Scenario names to run")
    parser.add_argument("--baseline", nargs="+", default=None, help="Baseline names to run")
    args = parser.parse_args()

    scenario_names = args.scenario or ["code_spec", "multi_task", "emotion"]
    baseline_names = args.baseline or ["skillmem", "memgpt_style", "sliding_window_rag"]

    print("╔══════════════════════════════════════════════════╗")
    print("║     mem-Engram 行业对标 Benchmark v1.0          ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"场景: {scenario_names}")
    print(f"基线: {baseline_names}")

    results = run_benchmark(scenario_names, baseline_names)
    generate_report(results)


if __name__ == "__main__":
    main()
