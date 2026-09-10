import uuid
import logging
from typing import Dict, Any, Optional
from app.core.celery_app import celery_app
from app.tasks.review_tasks import analyze_code_task

logger = logging.getLogger(__name__)

class ReviewService:
    
    @staticmethod
    def submit_task(code: Optional[str], github_url: Optional[str], language: str) -> tuple:
        task_id = str(uuid.uuid4())
        source_type = "code" if code else "github"
        code_content = code or "从 GitHub 获取的代码（待实现）"
        
        analyze_code_task.apply_async(
            args=[code_content, language],
            task_id=task_id
        )
        
        logger.info(f"Task {task_id} submitted to Celery, source_type={source_type}")
        return task_id, source_type
    
    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=celery_app)
        state = task_result.state
        
        status_map = {
            "PENDING": "PENDING",
            "STARTED": "PROCESSING",
            "PROGRESS": "PROCESSING",
            "SUCCESS": "SUCCESS",
            "FAILURE": "FAILED",
            "RETRY": "RETRYING"
        }
        
        response = {
            "task_id": task_id,
            "status": status_map.get(state, "PENDING")
        }
        
        if state == "SUCCESS":
            response["result"] = task_result.result
        elif state in ["FAILURE", "RETRY"]:
            response["error"] = str(task_result.info)
        elif state in ["STARTED", "PROGRESS"]:
            info = task_result.info or {}
            response["progress"] = info.get("progress", 0)
            response["step"] = info.get("step", "Processing...")
        
        return response
