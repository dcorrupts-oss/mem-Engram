"""
Code Specification Scenario
"""

SPEC_DESCRIPTIONS = {
    1: "变量命名规范（camelCase/snake_case）",
    2: "禁止var，只用let/const",
    3: "函数必须有JSDoc注释",
    5: "使用async/await，禁止.then",
    8: "禁止any类型",
    9: "必须使用try-catch错误处理",
    10: "常量大写命名",
}


def get_rounds():
    return [
        {"input": "请帮我创建一个Vue组件UserList.vue。规范：1. 变量用camelCase 2. 禁止var 3. 函数要JSDoc 4. async/await 5. 禁止any 6. try-catch 7. 常量大写", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
        {"input": "现在创建API层 api/user.js，同样的规范", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
        {"input": "创建状态管理 store/user.js", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
        {"input": "创建工具函数 utils/format.js", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
        {"input": "创建类型定义 types/user.d.ts", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
        {"input": "注意：从现在起，变量命名改成snake_case，其他规范不变", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
        {"input": "创建新的组件 UserProfile.vue，用snake_case", "check_spec": [1, 2, 3, 5, 8, 9, 10]},
    ]


def judge_code_spec(round_results):
    from benchmark.scenario_code_spec import check_spec_compliance
    total_checks = 0
    passed_checks = 0
    spec_results = []
    spec_change_ok = False

    for r in round_results:
        response = r.get("response", "")
        round_num = r.get("round", 0)
        spec_ids = r.get("check_spec", [])
        is_after_change = round_num > 5

        for spec_id in spec_ids:
            total_checks += 1
            result = check_spec_compliance(response, spec_id, is_after_change)
            if result["passed"]:
                passed_checks += 1
            spec_results.append({"round": round_num, **result})

    if round_results:
        last_round = round_results[-1]
        resp = last_round.get("response", "")
        snake_result = check_spec_compliance(resp, 1, is_after_change=True)
        spec_change_ok = snake_result["passed"]

    compliance_rate = passed_checks / total_checks if total_checks > 0 else 0
    change_bonus = 10 if spec_change_ok else 0
    score = round(compliance_rate * 80 + change_bonus, 1)

    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "compliance_rate": round(compliance_rate, 3),
        "spec_change_ok": spec_change_ok,
        "score": min(score, 100),
        "spec_results": spec_results,
    }


def check_spec_compliance(response, spec_id, is_after_change=False):
    import re
    spec_checks = {
        1: {
            "before_change": {
                "forbidden_patterns": [r'\bvar\s+\w+_\w+', r'(?:let|const)\s+\w+_\w+\s*='],
                "required_patterns": [r'(?:let|const)\s+[a-z][a-zA-Z0-9]*\s*='],
            },
            "after_change": {
                "forbidden_patterns": [r'\bvar\s+', r'(?:let|const)\s+[a-z][a-zA-Z]*[A-Z][a-zA-Z]*\s*='],
                "required_patterns": [r'(?:let|const)\s+[a-z][a-z0-9]*_[a-z0-9_]*\s*='],
            },
        },
        2: {"forbidden_patterns": [r'\bvar\s+'], "required_patterns": [r'\b(?:let|const)\s+']},
        3: {"forbidden_patterns": [], "required_patterns": [r'/\*\*[\s\S]*?\*/', r'@param|@returns|@description']},
        5: {"forbidden_patterns": [r'\.then\s*\('], "required_patterns": [r'await\s+']},
        8: {"forbidden_patterns": [r':\s*any\b', r'as\s+any\b', r'<any>'], "required_patterns": []},
        9: {"forbidden_patterns": [r'catch\s*\(\s*\)'], "required_patterns": [r'try\s*\{', r'catch\s*\(']},
        10: {"forbidden_patterns": [], "required_patterns": [r'[A-Z][A-Z_0-9]*\s*[=:]']},
    }

    check = spec_checks.get(spec_id)
    if not check:
        return {"spec_id": spec_id, "passed": True}

    if spec_id == 1 and is_after_change:
        config = check["after_change"]
    elif spec_id == 1:
        config = check["before_change"]
    else:
        config = check

    violations = []
    for pattern in config.get("forbidden_patterns", []):
        if re.search(pattern, response):
            violations.append(f"违反: {pattern}")

    missing = []
    for pattern in config.get("required_patterns", []):
        if not re.search(pattern, response):
            missing.append(f"缺少: {pattern}")

    has_code_block = bool(re.search(r'```[\s\S]*?```', response))
    if spec_id == 3 and has_code_block and not missing:
        code_blocks = re.findall(r'```[\s\S]*?```', response)
        has_jsdoc_in_code = any(re.search(r'@param|@returns|@description', block) for block in code_blocks)
        if not has_jsdoc_in_code:
            missing.append("代码块缺少JSDoc")

    passed = len(violations) == 0 and (len(missing) == 0 or not config.get("required_patterns"))
    return {"spec_id": spec_id, "passed": passed, "violations": violations, "missing": missing}
