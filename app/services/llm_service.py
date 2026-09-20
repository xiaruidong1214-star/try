import os
import json
import logging
from openai import OpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def generate_review(code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""你是一个代码审查专家。请分析以下 Python 代码：

{code}

已有 AST 分析结果：
- 时间复杂度：{analysis.get('complexity', 'UNKNOWN')}
- 循环嵌套深度：{analysis.get('max_loop_depth', 0)}
- 是否递归：{analysis.get('has_recursion', False)}

请返回 JSON 格式：
{{"summary": "一句话总结", "suggestions": ["建议1", "建议2"]}}"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        logger.info(f"LLM response: {content[:200]}")
        return json.loads(content)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {"summary": "LLM 分析暂不可用", "suggestions": []}
