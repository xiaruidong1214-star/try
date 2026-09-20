import json
import statistics
from collections import defaultdict
import redis
from config import REDIS_HOST, REDIS_PORT, REDIS_DB

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

COST_KEY = "llm:cost"
TOKEN_KEY = "llm:tokens"
TRACE_KEY = "llm:trace"
P99_KEY = "llm:cost:list"


def report_by_module():
    """按业务模块聚合成本"""
    out = defaultdict(lambda: {"cost": 0.0, "tokens": 0})
    for field, cost in r.hgetall(COST_KEY).items():
        session_id, module = field.split(":", 1)
        out[module]["cost"] += float(cost)
    for field, tokens in r.hgetall(TOKEN_KEY).items():
        session_id, module = field.split(":", 1)
        out[module]["tokens"] += int(tokens)
    return dict(out)


def report_by_session():
    """按会话聚合成本"""
    out = defaultdict(lambda: {"cost": 0.0, "tokens": 0})
    for field, cost in r.hgetall(COST_KEY).items():
        session_id, module = field.split(":", 1)
        out[session_id]["cost"] += float(cost)
    for field, tokens in r.hgetall(TOKEN_KEY).items():
        session_id, module = field.split(":", 1)
        out[session_id]["tokens"] += int(tokens)
    return dict(out)


def detect_p99_anomaly_by_module(threshold_ratio: float = 0.95):
    """
    按模块分别计算 P95，识别各模块内部的成本长尾
    """
    from collections import defaultdict

    module_costs = defaultdict(list)
    traces = r.lrange(TRACE_KEY, 0, -1)
    records = [json.loads(t) for t in traces]

    for rec in records:
        module_costs[rec["module"]].append(rec)

    result = {}
    for module, recs in module_costs.items():
        if len(recs) < 5:
            continue
        costs = sorted(r["cost"] for r in recs)
        idx = int(len(costs) * threshold_ratio)
        p95 = costs[min(idx, len(costs) - 1)]
        anomalies = [r for r in recs if r["cost"] > p95]
        result[module] = {
            "p95": round(p95, 6),
            "anomaly_count": len(anomalies),
            "total": len(recs),
        }
    return result


def detect_wasteful_retry(window_seconds: int = 60, threshold: int = 8):
    """
    无效重试识别：同一 session + prompt + module 在时间窗口内调用超过 threshold 次
    真实场景：接口超时后客户端自动重试，短时间内密集重复调用
    """
    from collections import defaultdict
    import time

    counter = defaultdict(list)
    traces = r.lrange(TRACE_KEY, 0, -1)
    now = time.time()

    for t in traces:
        rec = json.loads(t)
        # 只统计最近 window_seconds 内的调用
        if now - rec["ts"] > window_seconds:
            continue
        key = f"{rec['session_id']} / {rec['prompt_name']} / {rec['module']}"
        counter[key].append(rec)

    out = {}
    for key, records in counter.items():
        if len(records) > threshold:
            out[key] = {
                "calls": len(records),
                "total_cost": round(sum(r["cost"] for r in records), 6),
                "window_seconds": window_seconds,
            }
    return out


def summary():
    """总览"""
    traces = r.lrange(TRACE_KEY, 0, -1)
    total_calls = len(traces)
    total_cost = sum(float(c) for c in r.lrange(P99_KEY, 0, -1))

    wasteful = detect_wasteful_retry()
    wasteful_calls = sum(v["calls"] for v in wasteful.values())
    wasteful_cost = sum(v["cost"] for v in wasteful.values())

    return {
        "总调用次数": total_calls,
        "总成本（元）": round(total_cost, 6),
        "无效重试组合数": len(wasteful),
        "无效重试调用数": wasteful_calls,
        "无效重试成本（元）": round(wasteful_cost, 6),
        "无效消耗占比": f"{(wasteful_cost / total_cost * 100):.1f}%" if total_cost > 0 else "N/A",
    }