import json
import time
import redis
from celery import Celery
from config import (
    CELERY_BROKER, CELERY_BACKEND,
    REDIS_HOST, REDIS_PORT, REDIS_DB,
    MODEL_PRICING, DEFAULT_MODEL,
)

celery_app = Celery("llm_tracker", broker=CELERY_BROKER, backend=CELERY_BACKEND)

# 同步 Redis 客户端
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# 成本归因 Key 前缀
COST_KEY = "llm:cost"          # Hash: field=session:module, value=累计成本
TOKEN_KEY = "llm:tokens"       # Hash: field=session:module, value=累计Token
TRACE_KEY = "llm:trace"        # List: 每次调用的完整记录
P99_KEY = "llm:cost:list"      # List: 所有调用的成本，用于算 P99


def calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """按模型定价表算成本，未知模型走默认价"""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])
    return (
        input_tokens / 1000 * pricing["input"]
        + output_tokens / 1000 * pricing["output"]
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=2)
def record_metrics_task(self, session_id, prompt_name, module, model, input_tokens, output_tokens, elapsed):
    """Celery 异步任务：写 Redis，失败自动重试 3 次"""
    try:
        cost = calc_cost(model, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens
        field = f"{session_id}:{module}"

        pipe = r.pipeline()
        # 累计成本
        pipe.hincrbyfloat(COST_KEY, field, cost)
        # 累计 Token
        pipe.hincrby(TOKEN_KEY, field, total_tokens)
        # 记录调用明细
        record = {
            "session_id": session_id,
            "prompt_name": prompt_name,
            "module": module,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "elapsed": elapsed,
            "ts": time.time(),
        }
        pipe.lpush(TRACE_KEY, json.dumps(record))
        pipe.ltrim(TRACE_KEY, 0, 9999)  # 只保留最近 10000 条
        # 成本列表用于 P99
        pipe.lpush(P99_KEY, cost)
        pipe.ltrim(P99_KEY, 0, 9999)
        pipe.execute()

    except Exception as exc:
        # 失败自动重试
        raise self.retry(exc=exc)