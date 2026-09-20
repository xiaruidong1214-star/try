import time
from functools import wraps
from tasks import record_metrics_task

def track_llm(session_id: str, prompt_name: str, module: str = "default", model: str = "deepseek-chat"):
    """
    非侵入式装饰器：自动埋点，把计量数据丢进 Celery 异步队列
    - 计量失败不影响业务主流程（降级）
    - 被装饰函数需返回 dict，含 usage 字段
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # 降级：计量失败不影响主流程
            try:
                record_metrics_task.delay(
                    session_id=session_id,
                    prompt_name=prompt_name,
                    module=module,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    elapsed=elapsed,
                )
            except Exception as e:
                # 记录日志但不抛出，保证业务调用正常返回
                print(f"[tracker] 计量上报失败（已降级）: {e}")

            return result
        return wrapper
    return decorator