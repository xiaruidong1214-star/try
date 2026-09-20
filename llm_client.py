import os
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEFAULT_MODEL

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


def real_llm_call(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """
    真实调用 DeepSeek API
    返回格式与装饰器约定一致：含 usage 字段
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        },
    }