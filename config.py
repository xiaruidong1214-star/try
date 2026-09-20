import os

# ========== Redis ==========
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

# ========== Celery ==========
CELERY_BROKER = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
CELERY_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"

# ========== 多模型定价表（元 / 1K tokens）==========
# 按 2026 年量级估，可按实际调整
MODEL_PRICING = {
    "deepseek-chat":     {"input": 0.001, "output": 0.002},
    "deepseek-reasoner": {"input": 0.002, "output": 0.004},
    "gpt-4o":            {"input": 0.018, "output": 0.072},
    "gpt-4o-mini":       {"input": 0.001, "output": 0.004},
}

DEFAULT_MODEL = "deepseek-chat"

# ========== DeepSeek ==========
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"