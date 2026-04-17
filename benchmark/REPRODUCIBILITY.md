# mem-Engram Benchmark 可复现测试指南

## 快速开始

```bash
cd d:\Project\Research\mem-Engram\benchmark

# 默认运行（自动清缓存）
python runner.py

# 指定场景
python runner.py --scenario code_spec

# 指定基线
python runner.py --baseline skillmem

# 不清缓存（用于快速调试）
python runner.py --no-cache-clear
```

## 可复现性保证

本 benchmark 实现了以下机制确保结果可复现：

1. **评判器固定参数**：所有评判 LLM 调用使用 `temperature=0.1` + `seed=42`，保证评分确定性
2. **系统响应无 seed**：系统生成使用默认 temperature=0.7（无 seed），保持创造性
3. **自动清缓存**：每次运行前自动清理 `.cache` 目录，避免旧结果干扰
4. **完整 Token 统计**：包含所有 LLM 调用（atom 提取、路由、生成等）

## 预期结果

使用默认配置运行，应得到与 README 中一致的结果：

| 维度 | mem-Engram | MemGPT-style | RAG+窗口 |
|------|------------|--------------|----------|
| 代码规范 | ~91.4 | ~71.4 | ~62.9 |
| 多任务切换 | ~67.5 | ~72.5 | ~70.0 |
| 情感陪伴 | ~57.8 | ~57.5 | ~56.7 |
| **总分** | **~216.7** | **~201.4** | **~189.6** |

## 影响复现的因素

以下因素可能导致分数有 ±2-3 分波动：

- **Ollama 模型版本**：不同版本的 qwen3.5 可能有细微差异
- **系统负载**：高负载可能影响 LLM 输出质量
- **Python 版本**：不同版本的浮点数计算可能有微小差异

但核心排名（mem-Engram > RAG > MemGPT）应保持稳定。

## 验证复现性

运行两次相同配置，比较结果：

```bash
# 第一次
python runner.py
# 结果保存到 benchmark/results/benchmark_YYYYMMDD_HHMMSS.json

# 第二次
python runner.py
# 比较两次 JSON 文件的分数差异
```

## 故障排查

- **Ollama 无响应**：确保 `ollama serve` 正在运行
- **模型未下载**：运行 `ollama pull qwen3.5:latest`
- **分数异常**：检查是否使用了 `--no-cache-clear`，缓存可能导致旧结果复用
- **分数偏低**：确认 seed 参数只用于评判器，不应影响系统响应生成
