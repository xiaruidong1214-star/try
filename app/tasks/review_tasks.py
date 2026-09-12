import logging
from typing import Dict, Any, List
from app.core.celery_app import celery_app
from app.services.ast_analyzer import ComplexityAnalyzer
from app.services.llm_service import generate_review
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analyze_code")
def analyze_code_task(self, code: str, language: str = "python", cache_key: str = None):
    task_id = self.request.id
    logger.info(f"[Celery] Starting analysis for task {task_id}")
    
    try:
        self.update_state(state="STARTED", meta={"progress": 0, "step": "开始分析"})
        
        # 1. AST 解析
        self.update_state(state="PROGRESS", meta={"progress": 30, "step": "解析代码结构..."})
        analyzer = ComplexityAnalyzer()
        analysis_result = analyzer.analyze(code)
        
        # 2. 规则建议
        self.update_state(state="PROGRESS", meta={"progress": 50, "step": "生成基础建议..."})
        rule_suggestions = _generate_suggestions(analysis_result)
        
        # 3. LLM 深度分析
        self.update_state(state="PROGRESS", meta={"progress": 70, "step": "调用大模型分析..."})
        llm_result = generate_review(code, analysis_result)
        
        # 4. 组装结果
        result = {
            "complexity": analysis_result.get("complexity", "UNKNOWN"),
            "max_loop_depth": analysis_result.get("max_loop_depth", 0),
            "loop_count": analysis_result.get("loop_count", 0),
            "function_count": analysis_result.get("function_count", 0),
            "has_recursion": analysis_result.get("has_recursion", False),
            "total_lines": analysis_result.get("total_lines", 0),
            "comment_ratio": analysis_result.get("comment_ratio", 0),
            "suggestions": rule_suggestions,
            "llm_summary": llm_result.get("summary", ""),
            "llm_suggestions": llm_result.get("suggestions", []),
            "details": analysis_result.get("details", []),
            "language": language,
            "code_preview": code,  # 返回完整代码，让前端渲染
        }
        
        # ★ 5. 写入缓存
        if cache_key:
            cache_service.set(cache_key, result, ttl=3600)
        # ★ 6. 保存到数据库
        from app.models.database import save_review
        save_review(task_id, code, language, result)
        
        logger.info(f"[Celery] Task {task_id} completed, complexity={result['complexity']}")
        return result
        
    except Exception as e:
        logger.error(f"[Celery] Task {task_id} failed: {e}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e


def _generate_suggestions(analysis: Dict[str, Any]) -> List[str]:
    suggestions = []
    depth = analysis.get("max_loop_depth", 0)
    has_recursion = analysis.get("has_recursion", False)
    comment_ratio = analysis.get("comment_ratio", 0)
    
    if depth >= 3:
        suggestions.append(f"⚠️ 检测到 {depth} 层循环嵌套，复杂度极高")
    elif depth == 2:
        suggestions.append("⚠️ 检测到双层循环嵌套（O(n^2)）")
    elif depth == 1:
        suggestions.append("✅ 单层循环（O(n)），复杂度良好")
    
    if has_recursion:
        suggestions.append("💡 检测到递归调用，建议加缓存或改成迭代")
    
    if comment_ratio < 5:
        suggestions.append("📝 注释比例偏低（<5%）")
    
    if not suggestions:
        suggestions.append("✅ 代码结构良好")
    
    return suggestions