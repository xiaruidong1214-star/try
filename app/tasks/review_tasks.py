import logging
import time
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="analyze_code")
def analyze_code_task(self, code: str, language: str = "python"):
    task_id = self.request.id
    logger.info(f"[Celery] Starting analysis for task {task_id}")
    
    try:
        self.update_state(state="STARTED", meta={"progress": 0})
        
        self.update_state(state="PROGRESS", meta={"progress": 30, "step": "Parsing code..."})
        time.sleep(1)
        
        self.update_state(state="PROGRESS", meta={"progress": 60, "step": "Analyzing complexity..."})
        time.sleep(1)
        
        self.update_state(state="PROGRESS", meta={"progress": 80, "step": "Generating suggestions..."})
        time.sleep(1)
        
        result = {
            "complexity": "O(n^2) - 检测到双重循环嵌套",
            "suggestions": "建议使用双指针或哈希表优化时间复杂度",
            "language": language,
            "code_preview": code[:100] + "..." if len(code) > 100 else code,
            "analysis_time": "3 seconds"
        }
        
        logger.info(f"[Celery] Task {task_id} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"[Celery] Task {task_id} failed: {e}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
