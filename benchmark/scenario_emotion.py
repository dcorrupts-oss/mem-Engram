"""
Emotional Companionship Scenario
"""

def get_rounds():
    return [
        {"input": "我今天升职了！太开心了！终于熬出头了！", "emotion": "HIGH"},
        {"input": "我最好的朋友小李，我们认识十年了，他今天也为我高兴。", "emotion": "HIGH", "check_recall": ["朋友小李", "认识十年"]},
        {"input": "其实我一直很焦虑，压力很大，怕自己做不好。", "emotion": "LOW"},
        {"input": "我女朋友小美上周和我分手了，我们在一起三年...", "emotion": "LOW", "check_recall": ["女朋友小美", "分手", "三年"]},
        {"input": "帮我回忆一下，我最好的朋友叫什么？", "check_recall": ["小李"]},
        {"input": "今天天气不错，没什么特别的。", "emotion": "NEUTRAL"},
        {"input": "之前说我分手的事，你觉得我该怎么走出来？", "check_recall": ["分手", "小美"]},
        {"input": "你还记得我升职的事吗？", "check_recall": ["升职"]},
    ]


def judge_emotion_companion(round_results):
    from benchmark import call_llm
    total_recall = 0
    passed_recall = 0
    sensitivity_checks = 0
    sensitivity_passed = 0
    round_details = []

    for r in round_results:
        response = r.get("response", "")
        round_num = r.get("round", 0)
        emotion = r.get("emotion", "NEUTRAL")

        recall_facts = r.get("check_recall", [])
        recall_detail = []
        for fact in recall_facts:
            total_recall += 1
            judge_prompt = f"""请判断以下回复是否包含了用户提到的关键信息（语义层面，不要求逐字匹配）。

用户关键信息: "{fact}"
AI回复: "{response[:500]}"

请回答JSON: {{"contains": true/false, "reason": "简短说明"}}"""
            judge_resp, _, _, _ = call_llm([{"role": "user", "content": judge_prompt}], max_tokens=128, use_cache=False)
            found = False
            if "true" in judge_resp.lower() and "false" not in judge_resp.lower():
                found = True
                passed_recall += 1
            recall_detail.append({"fact": fact, "found": found})

        if emotion == "LOW" and "分手" in r.get("input", ""):
            sensitivity_checks += 1
            sens_prompt = f"""请判断以下回复是否以共情、温和的方式回应用户的分手痛苦，避免冷漠或说教。

AI回复: "{response[:500]}"

请回答JSON: {{"empathetic": true/false, "reason": "简短说明"}}"""
            sens_resp, _, _, _ = call_llm([{"role": "user", "content": sens_prompt}], max_tokens=128, use_cache=False)
            if "true" in sens_resp.lower() and "false" not in sens_resp.lower():
                sensitivity_passed += 1

        round_details.append({
            "round": round_num,
            "emotion": emotion,
            "recall_detail": recall_detail,
        })

    recall_rate = passed_recall / total_recall if total_recall > 0 else 0.0
    sensitivity_rate = sensitivity_passed / sensitivity_checks if sensitivity_checks > 0 else 0.0

    score = round(recall_rate * 40 + sensitivity_rate * 35 + 25, 1)

    return {
        "total_recall_checks": total_recall,
        "passed_recall_checks": passed_recall,
        "recall_rate": round(recall_rate, 3),
        "sensitivity_checks": sensitivity_checks,
        "sensitivity_passed": sensitivity_passed,
        "sensitivity_rate": round(sensitivity_rate, 3),
        "score": min(score, 100),
        "round_details": round_details,
    }
