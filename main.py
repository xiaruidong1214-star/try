import time
import random
from tracker import track_llm
from llm_client import real_llm_call
from report import (
    summary, report_by_module, report_by_session,
    detect_p99_anomaly_by_module, detect_wasteful_retry,
)


# ========== 三个业务模块的调用 ==========

@track_llm(session_id="user_001", prompt_name="review_v1", module="code_review")
def call_code_review(prompt: str):
    return real_llm_call(prompt)


@track_llm(session_id="user_002", prompt_name="chat_v2", module="chat_agent")
def call_chat_agent(prompt: str):
    return real_llm_call(prompt)


@track_llm(session_id="user_003", prompt_name="qa_v1", module="doc_qa")
def call_doc_qa(prompt: str):
    return real_llm_call(prompt)


# ========== 测试数据 ==========

SHORT_PROMPTS = [
    "什么是递归？一句话回答",
    "什么是闭包？一句话回答",
    "什么是协程？一句话回答",
    "什么是 GIL？一句话回答",
    "什么是装饰器？一句话回答",
]

LONG_PROMPTS = [
    "请详细解释 Python 的 GIL，包括它的历史、影响、以及多线程和多进程的适用场景，至少 300 字",
    "请详细解释数据库索引的原理，包括 B+ 树结构、聚簇索引和非聚簇索引的区别，至少 300 字",
    "请详细解释 HTTP 和 HTTPS 的区别，包括 TLS 握手过程、证书验证机制，至少 300 字",
]


def run_normal_traffic():
    """模拟正常流量：20 次短调用 + 5 次长调用"""
    for i in range(20):
        call_code_review(random.choice(SHORT_PROMPTS))
        call_chat_agent(random.choice(SHORT_PROMPTS))
        call_doc_qa(random.choice(SHORT_PROMPTS))

    for i in range(5):
        call_code_review(random.choice(LONG_PROMPTS))


def run_wasteful_retry():
    """
    模拟无效重试：同一 session + prompt + module 反复调用
    真实场景：接口超时后客户端自动重试，但每次携带完整上下文
    """
    for _ in range(6):
        call_code_review("什么是递归？一句话回答")


if __name__ == "__main__":
    print("开始跑测试流量...")
    print("注意：Celery Worker 必须已经在另一个窗口运行\n")

    # 1. 正常流量
    run_normal_traffic()

    # 2. 模拟无效重试
    run_wasteful_retry()

    # 3. 等 Celery 异步任务写完
    print("等待 Celery 异步任务处理...")
    time.sleep(5)

    # ========== 输出报表 ==========
    print("\n" + "=" * 50)
    print("P95 异常检测（按模块）")
    print("=" * 50)
    p95_result = detect_p99_anomaly_by_module()
    for module, stats in p95_result.items():
        print(f"  {module}: P95={stats['p95']} 元, 异常 {stats['anomaly_count']} / {stats['total']} 次")

    print("\n" + "=" * 50)
    print("无效重试识别（60 秒窗口内 > 3 次）")
    print("=" * 50)
    wasteful = detect_wasteful_retry(window_seconds=60, threshold=3)
    if wasteful:
        for k, v in wasteful.items():
            print(f"  {k}: {v['calls']} 次调用, 累计 {v['total_cost']:.6f} 元")
    else:
        print("  未检测到无效重试")