"""
Multi-Task Switching Scenario
"""

def get_rounds():
    return [
        {"input": "分析Q3财报：收入5000万，成本3200万，利润率36%。主要增长来自华东区。", "emotion": "NEUTRAL"},
        {"input": "华东区Q3收入占比多少？", "check_recall": ["华东区Q3收入"]},
        {"input": "帮我写一封开除张三的HR邮件，他连续三个月未达标。", "emotion": "NEUTRAL"},
        {"input": "邮件语气要正式但人性化。", "check_no_leak": ["5000万", "3200万", "利润率", "华东区"]},
        {"input": "回到刚才财报里利润率那个点再展开说说。", "check_recall": ["利润率36%", "华东区"]},
        {"input": "Q4预算规划：营销预算800万，研发1200万。", "emotion": "NEUTRAL"},
        {"input": "刚才说的HR邮件里，张三的部门是什么？", "check_no_leak": ["800万", "1200万", "预算"]},
        {"input": "继续说Q3财报，华东区具体数据。", "check_recall": ["华东区", "Q3"]},
    ]


def judge_multi_task(round_results):
    from benchmark import call_llm
    total_recall_checks = 0
    passed_recall_checks = 0
    total_leak_checks = 0
    leaked_count = 0
    task_results = []

    for r in round_results:
        response = r.get("response", "")
        round_num = r.get("round", 0)

        recall_facts = r.get("check_recall", [])
        leak_keywords = r.get("check_no_leak", [])

        recall_passed = 0
        recall_details = []
        for fact in recall_facts:
            total_recall_checks += 1
            judge_prompt = f"""请判断以下回复是否包含了来自之前对话的关键事实（语义层面，不要求逐字匹配）。

关键事实: "{fact}"
AI回复: "{response[:500]}"

请回答JSON: {{"contains": true/false, "reason": "简短说明"}}"""
            judge_resp, _, _, _ = call_llm([{"role": "user", "content": judge_prompt}], max_tokens=128, use_cache=False)
            found = "true" in judge_resp.lower() and "false" not in judge_resp.lower()
            if found:
                recall_passed += 1
                passed_recall_checks += 1
            recall_details.append({"fact": fact, "found": found})

        leak_passed = 0
        leak_details = []
        for kw in leak_keywords:
            total_leak_checks += 1
            leaked = kw in response
            if leaked:
                leaked_count += 1
            else:
                leak_passed += 1
            leak_details.append({"keyword": kw, "leaked": leaked})

        task_results.append({
            "round": round_num,
            "recall_details": recall_details,
            "leak_details": leak_details,
        })

    recall_rate = passed_recall_checks / total_recall_checks if total_recall_checks > 0 else 0.0
    leak_rate = leaked_count / total_leak_checks if total_leak_checks > 0 else 0.0
    noise_reduction = 1 - leak_rate

    score = round(recall_rate * 60 + noise_reduction * 40, 1)

    return {
        "total_recall_checks": total_recall_checks,
        "passed_recall_checks": passed_recall_checks,
        "recall_rate": round(recall_rate, 3),
        "total_leak_checks": total_leak_checks,
        "leaked_count": leaked_count,
        "leak_rate": round(leak_rate, 3),
        "noise_reduction": round(noise_reduction, 3),
        "score": min(score, 100),
        "task_results": task_results,
    }
